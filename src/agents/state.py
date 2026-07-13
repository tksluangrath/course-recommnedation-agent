"""
Shared LangGraph state schema for the course advisor agent.
"""

from __future__ import annotations

from typing import Annotated

from langchain.agents import AgentState
from langgraph.graph.message import add_messages


class CourseAdvisorState(AgentState):
    """Per-conversation state passed through the StateGraph.

    Extends the base ``AgentState`` (which already provides ``messages`` with
    the ``add_messages`` reducer) with the per-user profile fields tools need,
    keeping profile data scoped to a single thread instead of a shared
    module-level global.
    """

    # Redeclared for clarity/documentation; behavior inherited from AgentState.
    messages: Annotated[list, add_messages]

    user_id: str
    known_skills: list[str]
    goals: str
    hours_per_week: float

    # Written by the router node, read by the conditional edges and by the
    # clarify/confirm nodes. Plain overwrite semantics (no reducer): each
    # turn's router run replaces them. Tools never read these.
    route: str
    clarify_question: str
    mutation_field: str   # "goals" | "skills" | ""
    mutation_value: str
