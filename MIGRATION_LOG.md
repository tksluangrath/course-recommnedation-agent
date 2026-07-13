---
noteId: "9490bb807ef011f1a1c089868f995fb3"
tags: []

---

# Migration Log — LangGraph Upgrade

Tracks the move from `create_agent` (LangChain ReAct loop) to an explicit LangGraph `StateGraph`
with real persistence, control flow, and streaming. This file is the shared contract between
the orchestrator and every subagent — the state schema recorded here is authoritative; do not
redefine it in a later phase.

## Ground truth notes (read before Phase 2)

- Existing SQLite DB: `data/courses.db`, path resolved via `DB_PATH` env var, default
  `data/courses.db` (see `src/utils/database.py:142`). Used by `DatabaseManager` and
  `ProfileManager`. Any checkpointer added in Phase 3 must point at this same file — no second
  database.
- `src/tools/recommender_tools.py` module-level globals to remove in Phase 2: `_db`,
  `_content_rec`, `_hybrid_rec`, `_path_graph`, `_active_profile`, plus the `set_active_profile()`
  function.
- `src/agents/course_advisor.py` currently builds a `create_agent` ReAct agent and keeps
  per-session history in `self._histories` (plain dict, hard-truncated to the last 20 messages).
- Out of scope, no changes: `src/recommender/*.py` (`content_based.py`, `hybrid.py`,
  `path_graph.py`).
- Uncommitted, unrelated changes exist in the working tree on `docker-compose.yml`,
  `docker-entrypoint.sh`, `src/utils/database.py` — not part of this migration, left untouched
  per user instruction (2026-07-13).

## State schema

_Not yet defined — Phase 2 subagent will propose the `TypedDict` here. Every later phase must
build on this schema, not invent a divergent one._

## Phase status

| Phase | Status | Notes |
|---|---|---|
| 1 — Dependency fix | done | orchestrator, no subagent |
| 2 — Kill global profile hack | not started | |
| 3 — Persistence via checkpointer | not started | |
| 4 — Explicit control flow | not started | |
| 5 — Streaming | not started | |
| 6 — Long-term memory store | not started (optional, needs sign-off) | |

## Phase 1 — Dependency fix

Change: `requirements.txt` — bumped `langchain` pin, added `langgraph` and
`langgraph-checkpoint-sqlite`.

Exit criteria: clean install, `import langgraph` and `import langchain` succeed.

Result: PASS. Verified in a throwaway venv (not the project's), installed
`langchain>=1.0 langgraph>=0.6 langgraph-checkpoint-sqlite langchain-anthropic
langchain-ollama anthropic` — resolved to `langchain 1.3.13`, `langgraph 1.2.9`,
`langgraph-checkpoint-sqlite 3.1.0`. `from langchain.agents import create_agent`,
`from langgraph.graph import StateGraph`, `from langgraph.checkpoint.sqlite import
SqliteSaver`, and `from langgraph.types import interrupt` all import without error.
