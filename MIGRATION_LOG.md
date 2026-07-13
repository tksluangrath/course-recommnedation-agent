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

Defined in `src/agents/state.py` as `CourseAdvisorState`, extending LangChain's built-in
`AgentState` (which already supplies `messages: Annotated[list[AnyMessage], add_messages]`):

```python
class CourseAdvisorState(AgentState):
    messages: Annotated[list, add_messages]
    user_id: str
    known_skills: list[str]
    goals: str
    hours_per_week: float
```

Passed to `create_agent(..., state_schema=CourseAdvisorState)`. Callers supply `user_id`,
`known_skills`, `goals`, and `hours_per_week` on every `agent.invoke({...})` call alongside
`messages`. Tools that need per-user data (`create_learning_path`,
`estimate_learning_timeline`) declare `state: Annotated[CourseAdvisorState, InjectedState]` and
read `state["hours_per_week"]` — scoped to that single invocation, not a shared global.

## Phase status

| Phase | Status | Notes |
|---|---|---|
| 1 — Dependency fix | done | orchestrator, no subagent |
| 2 — Kill global profile hack | done | see Phase 2 section below |
| 3 — Persistence via checkpointer | done | see Phase 3 section below |
| 4 — Explicit control flow | done | see Phase 4 section below |
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

## Phase 2 — Kill global profile hack

Change:
- Added `src/agents/state.py` — new `CourseAdvisorState` TypedDict (see State schema above).
- `src/tools/recommender_tools.py` — removed `_active_profile` global and `set_active_profile()`.
  `create_learning_path` and `estimate_learning_timeline` now take a
  `state: Annotated[CourseAdvisorState, InjectedState]` parameter and read
  `state["hours_per_week"]` instead. `_db`, `_content_rec`, `_hybrid_rec`, `_path_graph` untouched
  (stateless shared recommenders, out of scope).
- `src/agents/course_advisor.py` — removed both `set_active_profile()` calls (in `__init__` and
  in the profile-update paths). `create_agent(...)` now passes `state_schema=CourseAdvisorState`.
  `chat()` passes `user_id`, `known_skills`, `goals`, `hours_per_week` on every `agent.invoke()`
  call, scoping profile data to that single call instead of a shared module global.

Exit criteria: zero references to `_active_profile`/`set_active_profile` anywhere in the repo;
`create_agent` graph builds and accepts the extra state keys on invoke.

Result: PASS.
- `grep -rn "_active_profile\|set_active_profile" --include="*.py" .` → no output (zero hits).
- Verified `create_agent(llm, tools=get_all_tools(), system_prompt=..., state_schema=CourseAdvisorState)`
  builds and `agent.invoke({"messages": [...], "user_id": ..., "known_skills": ..., "goals": ...,
  "hours_per_week": ...})` reaches model execution (using `FakeListChatModel`; it fails only on
  `bind_tools` inside the fake model, unrelated to state wiring).
- `tool.tool_call_schema` for `create_learning_path`/`estimate_learning_timeline` confirms the LLM
  never sees the injected `state` arg — only the real tool params.

Deviation from brief: none. `create_agent` in the installed `langchain==1.3.13` does support
`state_schema=` and `InjectedState`, so this phase used real per-request state injection rather
than a stopgap. `self._histories` per-session dict in `course_advisor.py` was intentionally left
alone (explicitly Phase 3's problem). `self._profile` itself is still one dict per
`CourseAdvisorAgent` instance (one instance per Streamlit session already, per the app's
existing session wiring), so no cross-session leak risk remains from the removed globals; a full
`StateGraph` rebuild and checkpointer-backed persistence are still Phase 3/4 work.

## Phase 3 — Persistence via checkpointer

Change: `src/agents/course_advisor.py` only.
- Added a `SqliteSaver` checkpointer, constructed from `self._profile_mgr._db.db_path` (reuses
  `DatabaseManager`'s already-resolved `DB_PATH`/`data/courses.db` path — no second literal, no
  second database file) via `sqlite3.connect(db_path, check_same_thread=False)`. Passed to
  `create_agent(..., checkpointer=self._checkpointer)`.
- `chat()` now keys every `agent.invoke()` call with `config={"configurable": {"thread_id": sid}}`
  (`sid` defaults to `self.user_id`, same keying scheme profiles already use) and only passes the
  new `HumanMessage` (+ profile-context `SystemMessage`) in — the checkpointer/`add_messages`
  reducer is the source of truth for history, not a Python dict.
- Removed `self._histories`, `self._session_id`'s bookkeeping dict, and `_get_history()`.
- Added `_condense_history()`: called at the top of `chat()`, uses
  `langchain_core.messages.trim_messages(..., max_tokens=3000, token_counter=self.llm)` to find
  which messages are still within budget; anything older than that is condensed into one LLM
  summary call and replaced in the checkpoint via `RemoveMessage(id=...)` + one new
  `SystemMessage` (via `agent.update_state`). Token-aware, and old content is preserved as a
  summary rather than dropped — not a blunt truncation.
- `get_history()` keeps its public signature; reimplemented to read
  `self.agent.get_state(config).values["messages"]` instead of a dict.
- `reset()` keeps its public signature; reimplemented to call
  `self._checkpointer.delete_thread(sid)` — `langgraph-checkpoint-sqlite==3.1.0`'s `SqliteSaver`
  does expose a real `delete_thread(thread_id)` API (confirmed via
  `[m for m in dir(SqliteSaver) if not m.startswith('_')]`), so no thread-id-suffix workaround was
  needed.

Exit criteria: zero `self._histories` references; single sqlite path referenced project-wide;
smoke test proves restart-persistence.

Result: PASS.
- `grep -rn "self\._histories" --include="*.py" .` → no output (zero hits).
- Single sqlite path: `src/utils/database.py:142` resolves
  `os.environ.get("DB_PATH", "data/courses.db")`; `course_advisor.py` reuses that exact resolved
  string via `self._profile_mgr._db.db_path` — no second literal introduced (the other
  `data/courses.db` hit at `database.py:591` is pre-existing, in `load_courses_to_database()`,
  untouched).
- Smoke test (stub `BaseChatModel` subclass standing in for a real LLM — no API keys needed;
  `bind_tools` returns `self` so `create_agent`'s tool-binding step is a no-op):
  1. `CourseAdvisorAgent(user_id="smoke_user")` (instance 1), `chat("What courses do you
     recommend for machine learning?")` → `"Sure, here are some course ideas!"`.
     `get_history()` → `[system: profile context, human: ..., ai: "Sure, here are some course
     ideas!"]`.
  2. Fresh `CourseAdvisorAgent(user_id="smoke_user")` (instance 2, simulating a process restart —
     new Python object, same `user_id`, same on-disk DB file). `get_history()` on instance 2
     returns the same three messages, loaded from the checkpoint on disk, not instance 1's memory.
  3. `agent2.reset()` → `get_history()` returns `[]`, confirming `delete_thread` actually clears
     the persisted thread (not just an in-memory no-op).

Deviation from brief: none. One note: the profile-context `SystemMessage` is re-appended on every
`chat()` call (as it was pre-Phase-3, just now persisted rather than rebuilt each turn) so that
mid-conversation profile edits (`/skills`, `/goal`, `/hours`) are reflected without extra
bookkeeping; `_condense_history()`'s token budget absorbs the resulting repeated system messages
along with the rest of the old history, so this doesn't grow unbounded.

## Phase 4 — Explicit control flow (StateGraph rebuild)

Change: `src/agents/course_advisor.py` (replaced `create_agent` with a compiled `StateGraph`),
`src/agents/state.py` (added router scratch fields).

Graph shape:
```
START -> router
router -(state["route"])-> clarify | confirm | agent
clarify -> agent      (after interrupt() resumes with the answer, appended as a HumanMessage)
confirm -> END        (mutation applied or declined)
agent   -(tool_calls?)-> tools | END
tools   -> agent      (normal tool-calling loop)
```
- `router`: one `llm.with_structured_output(RouterIntent)` call classifying the turn into
  `search`/`skill_gap`/`learning_path` (all → `route="agent"`, still handled by the existing
  9-tool tool-calling loop — the router does not hand-route individual tools),
  `needs_clarification` (→ `route="clarify"`), or `profile_mutation` (→ `route="confirm"`).
  Falls back to `route="agent"` on any router failure so a bad classification never breaks a turn.
- `clarify`: calls `interrupt({"type": "clarify", "question": ...})`, genuinely suspending the
  graph; the next `chat()` call resumes it with the user's answer.
- `confirm`: triggered before overwriting an already-non-empty `goals` or `known_skills` value;
  calls `interrupt({"type": "confirm", ...})` and only applies the mutation on a yes/y resume.
- `chat()`'s resume bridge: `_pending_interrupt(config)` reads `graph.get_state(config).next` +
  `task.interrupts[0].value`; if paused, the incoming message is fed via
  `graph.invoke(Command(resume=message), config)` instead of starting a fresh turn.
- Public API (`chat`, `get_history`, `reset`, `get_profile`, `update_profile`, `add_skills`,
  `display_profile`) unchanged in signature; `chat_cli.py`/`streamlit_app.py` need no changes for
  this phase.

Exit criteria: independent verification subagent reports 4/4 pass with evidence.

Result: PASS (4/4), both by the independent verification subagent and by the orchestrator's own
separate stub-LLM trace (`graph.get_state(config).next` shown non-empty at `('clarify',)` /
`('confirm',)` while paused, empty after resume; a `no` answer on confirm was shown to actually
block the write, a `yes` was shown to actually apply it).
1. Grep for `set_active_profile`/`_active_profile`/`self._histories` → zero hits.
2. `course_advisor.py`/`state.py` compile; module imports and constructs a `CompiledStateGraph`
   with a stubbed LLM; all 7 public method signatures unchanged.
3. Real interrupt trace: `.next` non-empty at both `clarify` and `confirm` pauses, empty after
   each resume; decline path leaves the profile field unchanged, accept path applies it.
4. `src/recommender/*.py` shows no diff; the pre-existing diffs on `docker-compose.yml`,
   `docker-entrypoint.sh`, `src/utils/database.py` are self-consistent with unrelated infra work
   (healthcheck/volume/env changes, WAL mode) — nothing graph/agent-related was added to them.

Known gap (flagged, not silently skipped): the confirm interrupt only covers the **conversational**
path (natural-language "set my goal to X" routed through `router → confirm`). `chat_cli.py`'s
`/goal`/`/skills` command handlers and `streamlit_app.py`'s sidebar "Save Goal"/"Save Skills"
buttons still call `update_profile()`/`add_skills()` directly with no confirmation gate. Closing
this means routing those direct-command paths through the graph too, which overlaps with Phase 5's
UI-integration work (a mid-command yes/no prompt doesn't fit `chat()`'s current blocking
string-return contract without the streaming rework Phase 5 owns) — carried forward as a Phase 5
consideration, not solved here.

Deviation from brief: the implementation subagent found the rebuild already present, uncommitted,
in the working tree (from an earlier dispatch of this same phase that was interrupted mid-run
before its file writes were reverted) and verified it in place rather than re-authoring working,
already-correct code. The orchestrator independently re-verified the interrupt/resume behavior
from scratch (see Result above) rather than accepting either subagent's report at face value.
