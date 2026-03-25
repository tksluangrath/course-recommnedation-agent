# Phase 6 — Streamlit Web Interface ✅

Phase 6 put a real UI on top of everything built in Phases 1–5. The entire CLI experience — chat, profile management, learning paths, skill gap analysis — is now in the browser. No backend changes were needed; the Streamlit app is purely a frontend layer that calls into the same `CourseAdvisorAgent` the CLI uses.

```bash
streamlit run app/streamlit_app.py
```

Open `http://localhost:8501`.

---

## Layout

Wide Streamlit layout: sidebar on the left for profile and navigation, main panel on the right for the chat.

The page is login-gated — nothing renders until you enter a username. On submit, `CourseAdvisorAgent(user_id=username)` loads the SQLite profile. Returning users see their skills and goal immediately in the sidebar. New users start fresh.

---

## Sidebar

### Profile display

Shows the current profile inline: skills as inline code tags (`` `Python` · `SQL` ``), goal as plain text, and two `st.metric` tiles for hours/week and preferred difficulty.

### Edit forms

Three expanders — **Add Skills**, **Set Goal**, **Set Hours/Week** — that call through to `agent.add_skills()` and `agent.update_profile()`. All changes persist to SQLite immediately. The profile cards refresh on the next rerun.

### Quick actions

Rather than building a separate form-to-agent bridge, quick actions just construct a natural-language message and inject it into the chat as a user bubble. The agent handles it through the normal tool-calling flow, conversation history stays coherent, and all 9 tools remain available.

| Quick action | What gets sent to the agent |
|---|---|
| Build Learning Path | `"Create a learning path for my goal: '{goal}' with {N} hours per week."` |
| Skill Gap Analysis | `"Analyze my skill gap for becoming a {target}. My current skills are: {skills}."` |

### Course catalog explorer

A filterable view of all 2,759 courses loaded from the cleaned CSV via `@st.cache_data` — loaded once per process, never per rerun. Filters: category, difficulty, minimum rating. Displays course name, university, level, rating, category, and estimated hours.

### Reset Chat

Calls `agent.reset()` (clears the agent's internal conversation state) and clears `st.session_state["messages"]` (clears the visible chat history). The profile in SQLite is untouched.

---

## Chat panel

### Message rendering

Every message in `st.session_state["messages"]` renders as a `st.chat_message` bubble. If an assistant message has a `chart_data` payload attached, the chart renders inside the same bubble right below the text.

### How responses get processed

When the last message in history is from the user and there's no reply yet, `_process_pending_message` runs:
1. Calls `agent.chat(content)` inside `st.spinner("Thinking...")`
2. Parses the response text for chart patterns
3. Appends the assistant reply (with optional chart data) to history
4. Calls `st.rerun()`

On re-entry, the last message is now from the assistant, so the function exits immediately — no infinite loop.

### Chat input

`st.chat_input(...)` is pinned to the bottom of the page regardless of where in the code it's called. Submit on Enter, appends to history, reruns.

---

## Inline charts

Charts are detected from the agent's text output by regex — no separate API calls, no structured data format required. The agent tools already produce consistent text output, so pattern matching is enough.

### Learning path timeline (Gantt)

Triggered when the response contains `"--- Timeline"`. The parser looks for lines like:
```
Weeks 1–20: Beginner (3 courses, ~160 hrs)
```
Handles both en-dash (`–`) and regular hyphen (`-`).

Rendered as a horizontal Plotly bar chart (`go.Bar` with `base=` offset for the Gantt effect). Each difficulty level is one bar spanning its week range. Color-coded: Beginner green, Intermediate blue, Advanced orange. Hover shows the level, week range, and total hours.

### Skill gap donut

Triggered when the response contains `"Skill Gap Analysis"` and `"Completion: X%"`.

Rendered as a Plotly donut chart (`go.Pie` with `hole=0.55`). "Skills Matched" in green, "Gap Remaining" in grey. A center annotation shows the percentage at 26px.

---

## Session state

```python
st.session_state = {
    "user_id": str | None,             # None → show login screen
    "agent":   CourseAdvisorAgent | None,  # created once per browser session
    "messages": [
        {"role": "user"|"assistant", "content": str, "chart_data": dict|None},
        ...
    ]
}
```

The agent lives in session state (not `@st.cache_resource`) because it's user-specific. A browser refresh resets the session, but the profile in SQLite survives — the user just logs back in.

---

## Visual theme

A custom dark theme is injected via `_apply_theme()` right after `st.set_page_config`. Everything is plain CSS via `st.markdown(..., unsafe_allow_html=True)`.

**Color palette:**

| Use | Value |
|---|---|
| App background | `#080c12` |
| Sidebar / cards | `#0d1117` |
| Borders | `#1a2638` |
| Primary text | `#cdd9ea` |
| Muted text | `#4a6278` |
| Teal accent | `#00c9a7` |
| Teal gradient | `#00c9a7 → #0076a8` |

**Highlights:** Inter font loaded from Google Fonts; Streamlit chrome (main menu, footer, deploy button) hidden; primary buttons have a teal gradient fill with a glow shadow; the chat input gets a teal focus ring; both charts match the dark background.

---

## Function inventory

| Function | What it does |
|---|---|
| `_apply_theme()` | Injects the full CSS block |
| `init_session_state()` | Sets defaults on first run |
| `load_courses()` | `@st.cache_data` CSV loader for the course catalog |
| `render_login_screen()` | Centered username card; returns name on submit |
| `render_sidebar(agent)` | Orchestrates the full sidebar |
| `_render_profile_cards(agent)` | Skill tags, goal, hours/level metrics |
| `_render_edit_forms(agent)` | Add skills / set goal / set hours expanders |
| `_render_quick_actions()` | Learning path and skill gap prefill forms |
| `_enqueue_user_message(content)` | Appends user message + triggers rerun |
| `_render_course_explorer()` | Filterable course catalog table |
| `render_chat_panel(agent)` | Main chat area orchestrator |
| `_render_empty_state()` | Welcome hero + suggested prompt cards |
| `_render_message_history()` | Renders all chat bubbles + inline charts |
| `_process_pending_message(agent)` | Calls agent for unanswered user messages |
| `_render_chat_input()` | Captures `st.chat_input` submission |
| `_extract_chart_data(response)` | Regex parser for chart trigger patterns |
| `_render_chart(chart_data)` | Dispatches to timeline or skill gap renderer |
| `_render_timeline_chart(rows)` | Plotly horizontal Gantt chart |
| `_render_skill_gap_chart(completion)` | Plotly donut with center annotation |

---

## Files

**Created:**
- `app/__init__.py` — Python package marker
- `app/streamlit_app.py` — complete Streamlit application

**Modified:** None — the web UI is a pure frontend layer over the Phase 1–5 backend.

---

**Next:** [Phase 7 — Docker](PHASE7_COMPLETE.md)
*Updated: February 2026*
