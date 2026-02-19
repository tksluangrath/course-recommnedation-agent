"""
Course Advisor Agent

A conversational AI agent that acts as a learning advisor, helping users
find courses, build learning paths, and analyze skill gaps. Uses LangChain
agent with Ollama or Claude as the LLM backend.
"""

import sys
from pathlib import Path
from typing import List, Optional

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from llm_config import LLMConfig
from recommender_tools import get_all_tools

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


class CourseAdvisorAgent:
    """Conversational course recommendation agent."""

    def __init__(self, provider: str = None, temperature: float = None):
        """Initialize the agent.

        Args:
            provider: LLM provider ("ollama" or "claude")
            temperature: LLM temperature
        """
        print("Initializing Course Advisor Agent...")

        # Get ChatModel (required for tool calling)
        self.llm = LLMConfig.get_chat_llm(provider=provider, temperature=temperature)

        # Load tools
        self.tools = get_all_tools()
        print(f"Loaded {len(self.tools)} tools: {[t.name for t in self.tools]}")

        # Create agent using LangChain v1.2 create_agent
        self.agent = create_agent(
            self.llm,
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT,
        )

        # Conversation history per session
        self._histories = {}
        self._session_id = "default"

        print("Agent ready!\n")

    def _get_history(self, session_id: str = None) -> list:
        sid = session_id or self._session_id
        if sid not in self._histories:
            self._histories[sid] = []
        return self._histories[sid]

    def chat(self, message: str, session_id: str = None) -> str:
        """Send a message and get a response.

        Args:
            message: User's message
            session_id: Optional session ID for multi-session support

        Returns:
            Agent's response text
        """
        sid = session_id or self._session_id
        history = self._get_history(sid)

        # Build messages: history + new message
        messages = list(history) + [HumanMessage(content=message)]

        try:
            result = self.agent.invoke({"messages": messages})

            # Extract the final AI response
            output_messages = result.get("messages", [])
            response_text = ""
            for msg in reversed(output_messages):
                if isinstance(msg, AIMessage) and msg.content:
                    response_text = msg.content
                    break

            if not response_text:
                response_text = "I'm not sure how to respond to that."

            # Update history
            history.append(HumanMessage(content=message))
            history.append(AIMessage(content=response_text))

            # Keep history manageable (last 20 messages = 10 exchanges)
            if len(history) > 20:
                history[:] = history[-20:]

            return response_text

        except Exception as e:
            return f"I encountered an error: {str(e)}\nPlease try rephrasing your question."

    def reset(self, session_id: str = None):
        """Clear conversation history."""
        sid = session_id or self._session_id
        if sid in self._histories:
            self._histories[sid].clear()
        print("Conversation history cleared.")

    def get_history(self, session_id: str = None) -> List:
        """Get conversation history."""
        return self._get_history(session_id)


if __name__ == "__main__":
    agent = CourseAdvisorAgent()

    # Quick test
    print("=" * 60)
    print("TESTING COURSE ADVISOR AGENT")
    print("=" * 60)

    response = agent.chat("What courses do you recommend for learning machine learning?")
    print(f"\nAgent: {response}")
