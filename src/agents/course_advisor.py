"""
Course Advisor Agent

A conversational AI agent that acts as a learning advisor, helping users
find courses, build learning paths, and analyze skill gaps. Uses LangChain
agent with Ollama or Claude as the LLM backend.
"""

import sqlite3
import sys
from pathlib import Path
from typing import List, Optional

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, RemoveMessage, trim_messages
from langgraph.checkpoint.sqlite import SqliteSaver

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from llm_config import LLMConfig
from recommender_tools import get_all_tools
from database import ProfileManager
from state import CourseAdvisorState

SYSTEM_PROMPT = """You are a friendly and knowledgeable learning advisor. Your job is to help \
users find the right courses, build personalized learning paths, and plan their education \
journey effectively.

You have access to a database of thousands of Coursera courses across many topics including \
Data Science, Computer Science, Business, and more.

Your capabilities:
- Search for courses by topic, interest, or description
- Find courses similar to ones the user already knows
- Recommend courses based on specific skills the user wants to learn
- Create structured learning paths (beginner to advanced) with estimated hours per course
- Estimate how long a learning path will take based on the user's available hours per week
- Analyze skill gaps and suggest courses to fill them in the optimal order (foundational skills first)
- Show prerequisite courses required before a specific target course
- Provide information about popular/trending skills

Guidelines:
- Be conversational and helpful. Ask clarifying questions when needed.
- When recommending courses, explain WHY each course is a good fit.
- Consider the user's current skill level when making recommendations.
- If the user mentions skills they have, factor that into your suggestions.
- When creating learning paths, mention the time commitment (hours per course, total weeks).
- When the user asks how long something takes, use the estimate_learning_timeline tool.
- If the user asks what to take before a course, use the get_prerequisite_path tool.
- When showing skill gaps, present missing skills in the recommended learning order.
- Keep responses concise but informative.
- If you don't have enough information, ask the user to be more specific.
"""

# Once a thread's persisted history exceeds this many tokens, older messages are
# condensed into a single summary SystemMessage instead of growing unbounded.
MAX_HISTORY_TOKENS = 3000


class CourseAdvisorAgent:
    """Conversational course recommendation agent."""

    def __init__(self, user_id: str = None, provider: str = None, temperature: float = None):
        """Initialize the agent.

        Args:
            user_id: Username for profile persistence (defaults to "default")
            provider: LLM provider ("ollama" or "claude")
            temperature: LLM temperature
        """
        print("Initializing Course Advisor Agent...")

        # User profile
        self.user_id = user_id or "default"
        self._profile_mgr = ProfileManager()
        self._profile = self._profile_mgr.load(self.user_id)

        # Get ChatModel (required for tool calling)
        self.llm = LLMConfig.get_chat_llm(provider=provider, temperature=temperature)

        # Load tools
        self.tools = get_all_tools()
        print(f"Loaded {len(self.tools)} tools: {[t.name for t in self.tools]}")

        # Checkpointer: persists conversation history to the same SQLite file
        # DatabaseManager/ProfileManager already use (reuse its resolved path,
        # don't duplicate the DB_PATH literal). SqliteSaver needs a raw
        # sqlite3.Connection, separate from ProfileManager's SQLAlchemy engine —
        # a second connection to the same file is expected/fine here.
        db_path = self._profile_mgr._db.db_path
        conn = sqlite3.connect(db_path, check_same_thread=False)
        self._checkpointer = SqliteSaver(conn)

        # Create agent using LangChain v1.2 create_agent. state_schema carries the
        # per-user profile fields (hours_per_week, etc.) through InjectedState so
        # tools read them from this invocation's state instead of a shared global.
        # checkpointer makes conversation history durable across process restarts,
        # keyed by thread_id (== session_id, defaults to user_id).
        self.agent = create_agent(
            self.llm,
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT,
            state_schema=CourseAdvisorState,
            checkpointer=self._checkpointer,
        )

        self._session_id = self.user_id

        print("Agent ready!\n")

    def _condense_history(self, config: dict) -> None:
        """Condense old messages in the checkpointed thread once they exceed a token budget.

        Replaces the old blunt "keep last 20 messages" truncation: older messages are
        summarized into a single SystemMessage via one LLM call (instead of silently
        dropped), then removed from the checkpoint via RemoveMessage. Recent messages
        (within the token budget) are left untouched.
        """
        state = self.agent.get_state(config)
        messages = state.values.get("messages", []) if state.values else []
        if not messages:
            return

        recent = trim_messages(
            messages,
            max_tokens=MAX_HISTORY_TOKENS,
            token_counter=self.llm,
            strategy="last",
        )
        older = messages[: len(messages) - len(recent)]
        if len(older) < 4:
            return  # not enough stale history yet to bother summarizing

        transcript = "\n".join(
            f"{m.type}: {m.content}" for m in older if getattr(m, "content", None)
        )
        summary_prompt = [
            SystemMessage(
                content="Summarize the following conversation between a user and a "
                "course-advisor assistant in 3-5 sentences, preserving stated goals, "
                "skills, and any decisions made."
            ),
            HumanMessage(content=transcript),
        ]
        summary = self.llm.invoke(summary_prompt).content

        self.agent.update_state(
            config,
            {
                "messages": [RemoveMessage(id=m.id) for m in older]
                + [SystemMessage(content=f"[Earlier conversation summary] {summary}")]
            },
        )

    def chat(self, message: str, session_id: str = None) -> str:
        """Send a message and get a response.

        Args:
            message: User's message
            session_id: Optional session ID for multi-session support

        Returns:
            Agent's response text
        """
        sid = session_id or self._session_id
        config = {"configurable": {"thread_id": sid}}

        self._condense_history(config)

        # Inject profile context as a SystemMessage alongside the new message.
        # The checkpointer, not a Python dict, is now the source of truth for
        # conversation history — we only ever pass the newest message(s) in.
        context = self._profile_mgr.get_context_string(self.user_id)
        prefix = [SystemMessage(content=context)] if context else []

        try:
            result = self.agent.invoke(
                {
                    "messages": prefix + [HumanMessage(content=message)],
                    "user_id": self.user_id,
                    "known_skills": self._profile.get("known_skills", []),
                    "goals": self._profile.get("goals", ""),
                    "hours_per_week": self._profile.get("hours_per_week", 10.0) or 10.0,
                },
                config=config,
            )

            # Extract the final AI response
            output_messages = result.get("messages", [])
            response_text = ""
            for msg in reversed(output_messages):
                if isinstance(msg, AIMessage) and msg.content:
                    response_text = msg.content
                    break

            if not response_text:
                response_text = "I'm not sure how to respond to that."

            return response_text

        except Exception as e:
            return f"I encountered an error: {str(e)}\nPlease try rephrasing your question."

    def reset(self, session_id: str = None):
        """Clear conversation history by deleting the checkpointed thread."""
        sid = session_id or self._session_id
        self._checkpointer.delete_thread(sid)
        print("Conversation history cleared.")

    def get_history(self, session_id: str = None) -> List:
        """Get conversation history for a session from the checkpointer."""
        sid = session_id or self._session_id
        config = {"configurable": {"thread_id": sid}}
        state = self.agent.get_state(config)
        if not state.values:
            return []
        return state.values.get("messages", [])

    def get_profile(self) -> dict:
        """Return the current user profile dict."""
        self._profile = self._profile_mgr.load(self.user_id)
        return self._profile

    def update_profile(self, **kwargs) -> dict:
        """Update profile fields, persisted for the next chat() call's state."""
        self._profile = self._profile_mgr.save(
            self.user_id, {**self._profile, **kwargs}
        )
        return self._profile

    def add_skills(self, skills: List[str]) -> List[str]:
        """Add skills to the user profile (deduplicated)."""
        updated = self._profile_mgr.add_skills(self.user_id, skills)
        self._profile['known_skills'] = updated
        return updated

    def display_profile(self) -> str:
        """Return formatted profile string for display."""
        return self._profile_mgr.format_display(self.user_id)


if __name__ == "__main__":
    agent = CourseAdvisorAgent()

    # Quick test
    print("=" * 60)
    print("TESTING COURSE ADVISOR AGENT")
    print("=" * 60)

    response = agent.chat("What courses do you recommend for learning machine learning?")
    print(f"\nAgent: {response}")
