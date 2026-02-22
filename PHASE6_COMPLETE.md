# Phase 6 Complete — Streamlit Web Interface

## Summary

Phase 6 built a full web UI on top of the Phases 1–5 backend — no backend changes required. The entire CLI experience (chat, profile management, learning paths, skill gap analysis) is now accessible through a browser with Plotly visualizations rendered automatically from the agent's text responses.

**Run the app:**
```bash
streamlit run app/streamlit_app.py
```

---

## What Was Built

### Layout

Chat-first layout with a wide Streamlit page:

- **Sidebar** — profile display, edit forms, quick action shortcuts, filterable course catalog
- **Main panel** — chat history with inline charts, pinned chat input at the bottom

### Login Screen

Centered username input. On submit, `CourseAdvisorAgent(user_id=username)` loads the user's SQLite profile. New users get a blank profile; returning users see their skills, goal, and hours/week immediately.

The page is login-gated via `st.stop()` — the sidebar and chat panel never render until a user_id is set.

---

### Sidebar Features

#### Profile Cards
Displays the current profile inline:
- Skills rendered as inline code tags: `` `Python` · `SQL` · `Pandas` ``
- Goal as plain text
- `st.metric` tiles for Hours/Week and preferred difficulty level

#### Edit Forms (3 expanders)

| Expander | What it does |
|---|---|
| **Add Skills** | Comma-separated text input → `agent.add_skills()` → profile refreshes |
| **Set Goal** | Text input → `agent.update_profile(goals=...)` → profile refreshes |
| **Set Hours/Week** | Number input (1–80, step 0.5) → `agent.update_profile(hours_per_week=...)` |

All edits persist to SQLite immediately. Profile cards update on the next rerun.

#### Quick Actions (2 expanders)

Rather than bypassing the agent, quick actions construct a natural-language message and inject it into the chat — keeping conversation history coherent and letting the agent use all its tools normally.

| Quick Action | Constructed message |
|---|---|
| **Build Learning Path** | `"Create a learning path for my goal: '{goal}' with {N} hours per week available."` |
| **Skill Gap Analysis** | `"Analyze my skill gap for becoming a {target}. My current skills are: {skills}."` |

On submit, the message appears in the chat as a user bubble and the agent responds in the next rerun.

#### Course Catalog Explorer

Filterable view of all 2,759 courses loaded from `data/processed/cleaned_courses.csv` via `@st.cache_data` (loaded once per process, not per rerun).

Filters: category multiselect, difficulty multiselect, minimum rating slider (0–5).

Displays: Course, University, Level, Rating, Category, Est. Hours — `height=300`, `hide_index=True`, `use_container_width=True`.

#### Reset Chat

Button at the bottom of the sidebar. Calls `agent.reset()` (clears agent's internal conversation state) AND clears `st.session_state["messages"]` (clears the chat display). Profile is not affected.

---

### Chat Panel

#### Message History
Every message in `st.session_state["messages"]` is rendered as a `st.chat_message` bubble (`"user"` or `"assistant"` role). If the message has a `chart_data` payload, the chart is rendered inside the same bubble immediately below the text.

#### Agent Response Processing
When the last message in history is from the user, `_process_pending_message` fires:
1. Calls `agent.chat(content)` inside `st.spinner("Thinking...")`
2. Parses the response for chart patterns via `_extract_chart_data(response)`
3. Appends the assistant message dict (with optional `chart_data`) to history
4. Calls `st.rerun()` — safe because on re-entry the last message is now `"assistant"` role, so the function exits immediately without an infinite loop

#### Chat Input
`st.chat_input(...)` — pinned to the bottom of the page by Streamlit's layout engine. Submits on Enter, appends user message, reruns.

---

### Inline Charts (Auto-Detected from Agent Output)

Charts are triggered by regex pattern matching on the agent's text response — no separate API calls needed.

#### Timeline Gantt Chart
Triggered when the response contains `"--- Timeline"` (from `create_learning_path` or `estimate_learning_timeline` tool output).

Parsed with:
```
Weeks 1–20: Beginner (3 courses, ~160 hrs)
Weeks 21–45: Intermediate (3 courses, ~200 hrs)
Weeks 46–75: Advanced (3 courses, ~240 hrs)
```

Rendered as a horizontal Plotly `go.Bar` Gantt chart:
- Each level = one bar spanning its week range (`base=` offset creates the Gantt effect)
- Color-coded: Beginner (#4CAF50 green), Intermediate (#2196F3 blue), Advanced (#FF5722 orange)
- Hover shows: level, week range, total hours
- `height=280`, no legend, x-axis = weeks

#### Skill Gap Donut Chart
Triggered when the response contains `"Skill Gap Analysis"` and `"Completion: X%"` (from `analyze_skill_gap` tool output).

Rendered as a Plotly `go.Pie` donut (`hole=0.55`):
- "Skills Matched" slice in green, "Gap Remaining" slice in light grey
- Center annotation shows the completion percentage at 26px font
- `height=280`

---

### Architecture

#### Session State

```python
st.session_state = {
    "user_id": str | None,            # gates login screen
    "agent":   CourseAdvisorAgent | None,  # one per browser session
    "messages": [                      # full chat history
        {"role": "user"|"assistant", "content": str, "chart_data": dict|None},
        ...
    ]
}
```

The agent is stored in `st.session_state` (not `@st.cache_resource`) because it is user-specific. It is created once per browser session and survives reruns. A browser refresh resets the session but profile data is safe in SQLite — the user just logs in again.

#### Regex Patterns

```python
TIMELINE_TRIGGER_RE  = re.compile(r"---\s*Timeline", re.IGNORECASE)
TIMELINE_ROW_RE      = re.compile(
    r"Weeks?\s+(\d+)\s*[–\-]\s*(\d+)\s*[:\s]+(\w+)\s*"
    r"\(\d+\s*courses?,\s*~(\d+)\s*hrs?\)", re.IGNORECASE
)
SKILL_GAP_TRIGGER_RE = re.compile(r"Skill\s+Gap\s+Analysis", re.IGNORECASE)
COMPLETION_RE        = re.compile(r"Completion:\s*(\d+(?:\.\d+)?)\s*%", re.IGNORECASE)
```

Both en-dash (`–`) and regular hyphen (`-`) are handled in `TIMELINE_ROW_RE`.

#### Data Loading

```python
@st.cache_data
def load_courses() -> pd.DataFrame
```

The cleaned CSV is loaded once per process and cached. Filter operations return new DataFrames and never mutate the cache.

---

---

## Visual Theme

After initial functionality was complete, a full custom CSS theme was applied to the app via `_apply_theme()` — a helper injected with `st.markdown(..., unsafe_allow_html=True)` immediately after `st.set_page_config`.

### Color Palette

| Token | Value | Used for |
|---|---|---|
| App background | `#0e1117` | Full-page dark background |
| Sidebar / cards | `#141920` | Sidebar, login card, chart backgrounds |
| Border | `#1e2a3a` | Sidebar border, card border, dividers |
| Primary text | `#d4dcea` | Chat message text |
| Muted text | `#5c7288` | Captions, sub-labels, secondary info |
| Teal accent | `#00bfa5` | Buttons, focus rings, hover states, metric values |
| Teal gradient | `#00bfa5 → #0097a7` | Primary button fill, avatar badge |

### CSS Injection (`_apply_theme`)

| Rule | Effect |
|---|---|
| `@import url(Inter)` | Loads Inter 300–700 from Google Fonts |
| `#MainMenu`, `footer`, `.stDeployButton` hidden | Strips Streamlit chrome |
| `.stApp { background: #0e1117 }` | Dark full-page background |
| `section[data-testid="stSidebar"]` | Dark sidebar with border |
| Primary button gradient | Teal `135deg` gradient fill, white text |
| Secondary buttons | Dark fill (`#1a2233`), teal border on hover |
| Chat message containers | `border-radius: 12px`, Inter font |
| Chat input textarea | Dark fill, teal focus ring (`box-shadow`) |
| `.stMetricValue` | `#00e5cc` teal, `1.4rem`, bold |
| Expander summaries | Grey default, teal when open |
| `.login-card` / `.login-title` / `.accent` | Login card box with teal "Advisor" word |
| Custom scrollbar | 6px, dark track, teal thumb on hover |

### Login Screen

Replaced plain `st.text_input` label with an HTML card:
```html
<div class="login-card">
  <div class="login-title">Course <span class="accent">Advisor</span></div>
  <div class="login-sub">AI-powered learning path planner — Coursera × LLM</div>
</div>
```
Username input and button render below the card inside the center column.

### Sidebar Avatar Badge

The sidebar header was replaced with an initials badge:
```html
<div style="display:flex;align-items:center;gap:0.75rem">
  <div style="background:linear-gradient(135deg,#00bfa5,#0097a7); border-radius:50%">{initials}</div>
  <div>{username}<br><small>Learning Profile</small></div>
</div>
```
Initials are `user_id[:2].upper()`.

### Plotly Dark Theme

Both inline charts updated to match the dark app background:

| Property | Value |
|---|---|
| `paper_bgcolor` | `#141920` |
| `plot_bgcolor` | `#141920` |
| `font.color` | `#9eb3cc` |
| `xaxis.gridcolor` | `#1e2a3a` |
| `legend.bgcolor` | `#141920` |

---

## Files Created

| File | Description |
|---|---|
| `app/__init__.py` | Empty Python package marker |
| `app/streamlit_app.py` | Complete Streamlit application with custom CSS theme |

## Files Modified

None — the entire web UI is built on top of the existing backend without touching any Phase 1–5 code.

---

## Function Inventory

| Function | Purpose |
|---|---|
| `_apply_theme()` | Inject custom CSS: dark background, teal accents, Inter font, hidden chrome |
| `init_session_state()` | Initialize all session_state keys with safe defaults |
| `load_courses()` | `@st.cache_data` CSV loader for the course catalog |
| `render_login_screen()` | Centered username input; returns name on submit |
| `render_sidebar(agent)` | Sidebar orchestrator |
| `_render_profile_cards(agent)` | Skill tags, goal text, hrs/week + level metrics |
| `_render_edit_forms(agent)` | Add skills / set goal / set hours expanders |
| `_render_quick_actions()` | Learning path and skill gap prefill forms |
| `_enqueue_user_message(content)` | Append user message + trigger rerun |
| `_render_course_explorer()` | Filterable course catalog table |
| `render_chat_panel(agent)` | Main chat area orchestrator |
| `_render_message_history()` | Render all chat bubbles + inline charts |
| `_process_pending_message(agent)` | Call agent for unanswered user message |
| `_render_chat_input()` | Capture `st.chat_input` submission |
| `_extract_chart_data(response)` | Regex-parse response for chart trigger patterns |
| `_render_chart(chart_data)` | Dispatch to timeline or skill gap renderer |
| `_render_timeline_chart(rows)` | Plotly horizontal Gantt bar chart |
| `_render_skill_gap_chart(completion)` | Plotly donut chart with center annotation |

---

## Verification

| Test | Expected Result |
|---|---|
| `streamlit run app/streamlit_app.py` | App opens at `localhost:8501` |
| Enter username → Start Learning | Agent loads (spinner), sidebar shows profile |
| Returning user (e.g. "alice" with saved skills) | Skills + goal appear in sidebar immediately |
| Add skills via sidebar form | Tags update in profile cards after rerun |
| Type "Create a learning path for data science, 10 hrs/week" | Agent responds with path + Gantt chart appears below |
| Type "Analyze my skill gap for machine learning, I know Python" | Agent responds with gap analysis + donut chart appears |
| Use "Build Learning Path" quick action | Pre-filled message appears in chat, agent responds |
| Open "Browse Courses" in sidebar, filter by Data Science + Beginner | Table shows filtered subset with row count |
| Click "Reset Chat" | Chat history clears, profile unchanged |
| Refresh browser, re-enter same username | Profile reloads from SQLite, chat history empty |

---

## Tech Notes

- `st.set_page_config` is the first Streamlit call in the file — required by Streamlit
- `st.stop()` halts rendering on the login screen; prevents `AttributeError` on `None` agent
- All sidebar widgets have explicit `key=` arguments to avoid `DuplicateWidgetID` errors
- `st.chat_input` is always pinned to the bottom of the page regardless of call location
- Profile data survives browser refresh (SQLite); chat history does not (session state)

---

**Status**: Phase 6 Complete
**Next**: Project feature-complete across all 6 phases
**Updated**: February 22, 2026
