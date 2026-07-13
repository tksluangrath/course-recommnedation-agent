"""
Course Advisor Agent

A conversational AI agent that acts as a learning advisor, helping users
find courses, build learning paths, and analyze skill gaps. Uses LangChain
agent with Ollama or Claude as the LLM backend.
"""

import sqlite3
import sys
from pathlib import Path
from typing import List, Literal

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, RemoveMessage, trim_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt, Command
from pydantic import BaseModel, Field

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

ROUTER_PROMPT = """You are the intent router for a course-advisor assistant. Read the user's \
latest message (plus any conversation context) and classify it into exactly ONE category:

- "search": finding courses, similar courses, course details, popular/trending skills, or \
prerequisite chains — anything answerable by searching the catalogue.
- "skill_gap": the user wants to know which skills or courses they're missing for a goal.
- "learning_path": the user wants a structured multi-level plan or a timeline estimate.
- "needs_clarification": the request is too vague to act on and no topic/goal is recoverable \
from context (e.g. "build me a learning path" with no subject stated anywhere). Put a single \
specific unblocking question in `clarifying_question`.
- "profile_mutation": the user is asking to CHANGE their saved profile — set/replace their \
goal, or add skills (e.g. "set my goal to X", "add Python and SQL to my skills"). Set \
`profile_field` to "goals" or "skills" and `profile_value` to the new value (for skills, a \
comma-separated list).

Only pick "needs_clarification" when you genuinely cannot proceed. If the user names any topic, \
prefer an actionable category."""


class RouterIntent(BaseModel):
    """Structured classification the router node extracts from the user's message."""

    category: Literal[
        "search", "skill_gap", "learning_path", "needs_clarification", "profile_mutation"
    ] = Field(description="The single best-fit intent category.")
    clarifying_question: str = Field(
        default="", description="A specific question to ask, only when category is needs_clarification."
    )
    profile_field: Literal["goals", "skills", ""] = Field(
        default="", description="Which profile field to change, only when category is profile_mutation."
    )
    profile_value: str = Field(
        default="", description="The new value for the field, only when category is profile_mutation."
    )


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
        self._llm_with_tools = self.llm.bind_tools(self.tools)
        self._router_llm = self.llm.with_structured_output(RouterIntent)

        # Checkpointer: persists conversation history to the same SQLite file
        # DatabaseManager/ProfileManager already use (reuse its resolved path,
        # don't duplicate the DB_PATH literal). SqliteSaver needs a raw
        # sqlite3.Connection, separate from ProfileManager's SQLAlchemy engine —
        # a second connection to the same file is expected/fine here.
        db_path = self._profile_mgr._db.db_path
        conn = sqlite3.connect(db_path, check_same_thread=False)
        self._checkpointer = SqliteSaver(conn)

        self.graph = self._build_graph()
        self._session_id = self.user_id

        print("Agent ready!\n")

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------
    def _build_graph(self):
        """Compile the explicit StateGraph.

        Control flow:
            START -> router
            router -(route)-> clarify | confirm | agent
            clarify -> agent      (after interrupt() resumes with the answer)
            confirm -> END        (mutation done or cancelled)
            agent   -(tools?)-> tools | END
            tools   -> agent      (tool-calling loop)

        The router is one LLM structured-output call that buckets the turn into
        the normal tool-calling agent vs. a clarify interrupt vs. a
        profile-mutation confirm interrupt — it does NOT hand-route to each of
        the 9 tools, that stays the agent/ToolNode loop's job.
        """
        g = StateGraph(CourseAdvisorState)
        g.add_node("router", self._router_node)
        g.add_node("clarify", self._clarify_node)
        g.add_node("confirm", self._confirm_node)
        g.add_node("agent", self._agent_node)
        g.add_node("tools", ToolNode(self.tools))

        g.add_edge(START, "router")
        g.add_conditional_edges(
            "router",
            lambda s: s.get("route", "agent"),
            {
                "clarify": "clarify",
                "confirm": "confirm",
                "agent": "agent",
            },
        )
        g.add_edge("clarify", "agent")
        g.add_edge("confirm", END)
        g.add_conditional_edges(
            "agent",
            lambda s: "tools" if getattr(s["messages"][-1], "tool_calls", None) else END,
            {"tools": "tools", END: END},
        )
        g.add_edge("tools", "agent")

        return g.compile(checkpointer=self._checkpointer)

    @staticmethod
    def _last_human(messages) -> str:
        """Content of the most recent HumanMessage, or '' if none."""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                return m.content or ""
        return ""

    # ------------------------------------------------------------------
    # Graph nodes
    # ------------------------------------------------------------------
    def _router_node(self, state: CourseAdvisorState) -> dict:
        """Classify the turn and stash the decision in routing state fields.

        Degrades safely: any router failure falls through to the normal agent
        path rather than breaking the turn.
        """
        text = self._last_human(state["messages"])
        try:
            intent = self._router_llm.invoke(
                [SystemMessage(content=ROUTER_PROMPT), HumanMessage(content=text)]
            )
        except Exception:
            return {"route": "agent", "clarify_question": "", "mutation_field": "", "mutation_value": ""}

        route = "agent"
        if intent.category == "needs_clarification":
            route = "clarify"
        elif intent.category == "profile_mutation" and intent.profile_field:
            route = "confirm"
        return {
            "route": route,
            "clarify_question": intent.clarifying_question,
            "mutation_field": intent.profile_field,
            "mutation_value": intent.profile_value,
        }

    def _clarify_node(self, state: CourseAdvisorState) -> dict:
        """Pause execution with a clarifying question, resume with the user's answer.

        interrupt() suspends the whole graph run; the caller sees the question,
        and the NEXT chat() call resumes here (via Command(resume=...)) with the
        answer, which we append as a HumanMessage before flowing on to the agent.
        """
        question = state.get("clarify_question") or "Could you tell me more about what you're looking for?"
        answer = interrupt({"type": "clarify", "question": question})
        return {"messages": [HumanMessage(content=answer)]}

    def _confirm_node(self, state: CourseAdvisorState) -> dict:
        """Apply a profile mutation, but interrupt for confirmation first if it
        would overwrite an already-set field.
        """
        field = state.get("mutation_field", "")
        value = (state.get("mutation_value") or "").strip()
        if not field or not value:
            return {"messages": [AIMessage(content="I couldn't tell what to update — could you rephrase?")]}

        profile = self._profile_mgr.load(self.user_id)
        if field == "goals":
            current = (profile.get("goals") or "").strip()
            already_set = bool(current)
            question = (
                f"You already have a goal set: '{current}'. Replace it with '{value}'? (yes/no)"
            )
        else:  # skills
            current = profile.get("known_skills") or []
            already_set = bool(current)
            question = (
                f"You already have skills recorded ({', '.join(current)}). "
                f"Add '{value}' to them? (yes/no)"
            )

        if already_set:
            answer = interrupt({"type": "confirm", "field": field, "question": question})
            if str(answer).strip().lower() not in ("yes", "y"):
                keep = "goal" if field == "goals" else "skills"
                return {"messages": [AIMessage(content=f"Okay, keeping your existing {keep} unchanged.")]}

        if field == "goals":
            self.update_profile(goals=value)
            return {"messages": [AIMessage(content=f"Done — your goal is now '{value}'.")]}
        skills = [s.strip() for s in value.split(",") if s.strip()]
        updated = self.add_skills(skills)
        return {"messages": [AIMessage(content=f"Done — your skills are now: {', '.join(updated)}.")]}

    def _agent_node(self, state: CourseAdvisorState) -> dict:
        """Normal tool-calling LLM step. Loops with the ToolNode until no tool calls remain."""
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
        response = self._llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def _condense_history(self, config: dict) -> None:
        """Condense old messages in the checkpointed thread once they exceed a token budget.

        Replaces the old blunt "keep last 20 messages" truncation: older messages are
        summarized into a single SystemMessage via one LLM call (instead of silently
        dropped), then removed from the checkpoint via RemoveMessage. Recent messages
        (within the token budget) are left untouched.
        """
        state = self.graph.get_state(config)
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

        self.graph.update_state(
            config,
            {
                "messages": [RemoveMessage(id=m.id) for m in older]
                + [SystemMessage(content=f"[Earlier conversation summary] {summary}")]
            },
        )

    def _pending_interrupt(self, config: dict):
        """Return the interrupt payload if the thread is paused at one, else None.

        A paused graph reports the interrupted node in `snapshot.next` and carries
        the interrupt value on that task. Reading it from state (rather than the
        invoke() return shape) keeps this robust across langgraph versions.
        """
        snap = self.graph.get_state(config)
        if not snap.next:
            return None
        for task in snap.tasks:
            if task.interrupts:
                return task.interrupts[0].value
        return None

    def chat(self, message: str, session_id: str = None) -> str:
        """Send a message and get a response.

        If the thread is currently paused at a clarify/confirm interrupt, this
        message is treated as the resume answer (not a fresh turn). Otherwise it
        starts a new turn through the router. When a turn pauses at an interrupt,
        the returned string is the pending question; the next chat() call resumes.

        Args:
            message: User's message (or the answer to a pending question)
            session_id: Optional session ID for multi-session support

        Returns:
            Agent's response text, or the pending clarify/confirm question
        """
        sid = session_id or self._session_id
        config = {"configurable": {"thread_id": sid}}

        try:
            if self._pending_interrupt(config) is not None:
                # Thread is paused — resume the interrupted node with this answer.
                result = self.graph.invoke(Command(resume=message), config=config)
            else:
                self._condense_history(config)
                # Inject profile context as a SystemMessage alongside the new message.
                # The checkpointer, not a Python dict, is the source of truth for
                # history — we only ever pass the newest message(s) in.
                context = self._profile_mgr.get_context_string(self.user_id)
                prefix = [SystemMessage(content=context)] if context else []
                result = self.graph.invoke(
                    {
                        "messages": prefix + [HumanMessage(content=message)],
                        "user_id": self.user_id,
                        "known_skills": self._profile.get("known_skills", []),
                        "goals": self._profile.get("goals", ""),
                        "hours_per_week": self._profile.get("hours_per_week", 10.0) or 10.0,
                    },
                    config=config,
                )

            # Did this run pause at an interrupt? Surface the question as the reply.
            pending = self._pending_interrupt(config)
            if pending is not None:
                return pending.get("question", "Could you clarify that?")

            # Otherwise return the final AI response.
            for msg in reversed(result.get("messages", [])):
                if isinstance(msg, AIMessage) and msg.content:
                    return msg.content
            return "I'm not sure how to respond to that."

        except Exception as e:
            return f"I encountered an error: {str(e)}\nPlease try rephrasing your question."

    def stream_chat(self, message: str, session_id: str = None):
        """Stream a response token-by-token instead of blocking for the full reply.

        Same resume/interrupt semantics as chat(): if the thread is paused at a
        clarify/confirm interrupt, `message` is treated as the resume answer.
        Yields plain string chunks — either LLM tokens from the "agent" node as
        they're generated, or (for an interrupt pause, or a confirm/clarify node
        that built its reply directly without an LLM call) the whole reply as a
        single chunk. Callers don't need to special-case interrupts: just print
        every yielded chunk as it arrives.

        Args:
            message: User's message (or the answer to a pending question)
            session_id: Optional session ID for multi-session support

        Yields:
            str: response chunks, in order, forming the full reply when joined
        """
        sid = session_id or self._session_id
        config = {"configurable": {"thread_id": sid}}

        try:
            if self._pending_interrupt(config) is not None:
                stream_input = Command(resume=message)
            else:
                self._condense_history(config)
                context = self._profile_mgr.get_context_string(self.user_id)
                prefix = [SystemMessage(content=context)] if context else []
                stream_input = {
                    "messages": prefix + [HumanMessage(content=message)],
                    "user_id": self.user_id,
                    "known_skills": self._profile.get("known_skills", []),
                    "goals": self._profile.get("goals", ""),
                    "hours_per_week": self._profile.get("hours_per_week", 10.0) or 10.0,
                }

            streamed_any = False
            for chunk, metadata in self.graph.stream(
                stream_input, config=config, stream_mode="messages"
            ):
                if metadata.get("langgraph_node") == "agent" and getattr(chunk, "content", None):
                    streamed_any = True
                    yield chunk.content

            # Paused at a clarify/confirm interrupt: surface the question as one chunk.
            pending = self._pending_interrupt(config)
            if pending is not None:
                yield pending.get("question", "Could you clarify that?")
                return

            # confirm_node builds its AIMessage directly (no LLM call), so nothing
            # streamed above — fall back to the final state's last AIMessage.
            if not streamed_any:
                for msg in reversed(self.graph.get_state(config).values.get("messages", [])):
                    if isinstance(msg, AIMessage) and msg.content:
                        yield msg.content
                        return
                yield "I'm not sure how to respond to that."

        except Exception as e:
            yield f"I encountered an error: {str(e)}\nPlease try rephrasing your question."

    def reset(self, session_id: str = None):
        """Clear conversation history by deleting the checkpointed thread."""
        sid = session_id or self._session_id
        self._checkpointer.delete_thread(sid)
        print("Conversation history cleared.")

    def get_history(self, session_id: str = None) -> List:
        """Get conversation history for a session from the checkpointer."""
        sid = session_id or self._session_id
        config = {"configurable": {"thread_id": sid}}
        state = self.graph.get_state(config)
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
