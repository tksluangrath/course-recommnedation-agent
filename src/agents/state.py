"""
Shared LangGraph state schema for the course advisor agent.

This is the authoritative state contract (see MIGRATION_LOG.md) — later phases
(checkpointer persistence, explicit StateGraph control flow, streaming) build on
this schema rather than redefining it. Keep it minimal: only fields tools or
graph nodes actually read/write.
"""

from __future__ import annotations

from typing import Annotated

from langchain.agents import AgentState
from langgraph.graph.message import add_messages


class CourseAdvisorState(AgentState):
    """Per-conversation state passed through the agent/graph.

    Extends the base ``AgentState`` (which already provides ``messages`` with
    the ``add_messages`` reducer) with the per-user profile fields tools need.
    Passing this via ``create_agent(..., state_schema=CourseAdvisorState)`` and
    supplying the extra keys on each ``invoke()`` call keeps profile data scoped
    to a single request/session instead of a shared module-level global.
    """

    # Redeclared for clarity/documentation; behavior inherited from AgentState.
    messages: Annotated[list, add_messages]

    user_id: str
    known_skills: list[str]
    goals: str
    hours_per_week: float

    # Phase 4 routing scratch fields, written by the router node and read by the
    # graph's conditional edges / clarify+confirm nodes. Plain overwrite semantics
    # (no reducer): each turn's router run replaces them. Tools never read these.
    route: str
    clarify_question: str
    mutation_field: str   # "goals" | "skills" | ""
    mutation_value: str
