"""
Course Advisor — Streamlit Web Interface (Phase 6)

Chat-first UI wrapping the CourseAdvisorAgent backend.
Sidebar: profile management, quick actions, course catalog explorer.
Main panel: chat history, inline Plotly charts, chat input.

Run:
    streamlit run app/streamlit_app.py
"""

import sys
import os

# Wire src/ subdirectories before any project imports
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ["src/agents", "src/utils", "src/tools", "src/recommender"]:
    sys.path.insert(0, os.path.join(_ROOT, _sub))

import re
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from course_advisor import CourseAdvisorAgent

# ---------------------------------------------------------------------------
# Theme / CSS injection
# ---------------------------------------------------------------------------

def _apply_theme() -> None:
    """Inject custom CSS: dark background, teal accents, Inter font, hide Streamlit chrome."""
    st.markdown(
        """
        <style>
        /* ── Google Font ─────────────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        /* ── Hide Streamlit chrome ───────────────────────────────────── */
        #MainMenu            { visibility: hidden; }
        footer               { visibility: hidden; }
        .stDeployButton      { display: none; }
        header[data-testid="stHeader"] { background: transparent; }

        /* ── Global resets ───────────────────────────────────────────── */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* ── App background ──────────────────────────────────────────── */
        .stApp {
            background-color: #0e1117;
        }

        /* ── Main content column ─────────────────────────────────────── */
        .main .block-container {
            padding-top: 2rem;
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 900px;
        }

        /* ── Sidebar ─────────────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background-color: #141920;
            border-right: 1px solid #1e2530;
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: #e0e6ef;
        }

        /* ── Primary buttons ─────────────────────────────────────────── */
        .stButton > button[kind="primary"],
        .stButton > button[data-testid*="primary"] {
            background: linear-gradient(135deg, #00bfa5, #0097a7);
            color: #fff;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            letter-spacing: 0.3px;
            transition: opacity 0.2s ease;
        }
        .stButton > button[kind="primary"]:hover {
            opacity: 0.88;
        }

        /* ── Secondary buttons ───────────────────────────────────────── */
        .stButton > button {
            border-radius: 8px;
            border: 1px solid #2a3445;
            background-color: #1a2233;
            color: #c9d6e8;
            transition: border-color 0.2s ease;
        }
        .stButton > button:hover {
            border-color: #00bfa5;
            color: #00bfa5;
        }

        /* ── Chat messages ───────────────────────────────────────────── */
        .stChatMessage {
            border-radius: 12px;
            padding: 4px 0;
        }
        [data-testid="stChatMessageContent"] p {
            line-height: 1.7;
            color: #d4dcea;
        }

        /* ── Chat input ──────────────────────────────────────────────── */
        .stChatInputContainer textarea {
            background-color: #161d27;
            border: 1px solid #2a3445;
            border-radius: 12px;
            color: #d4dcea;
            font-family: 'Inter', sans-serif;
        }
        .stChatInputContainer textarea:focus {
            border-color: #00bfa5;
            box-shadow: 0 0 0 2px rgba(0,191,165,0.18);
        }

        /* ── Text inputs ─────────────────────────────────────────────── */
        .stTextInput input, .stNumberInput input {
            background-color: #161d27;
            border: 1px solid #2a3445;
            border-radius: 8px;
            color: #d4dcea;
            font-family: 'Inter', sans-serif;
        }
        .stTextInput input:focus, .stNumberInput input:focus {
            border-color: #00bfa5;
            box-shadow: 0 0 0 2px rgba(0,191,165,0.15);
        }

        /* ── Metric cards ────────────────────────────────────────────── */
        [data-testid="stMetricValue"] {
            font-size: 1.4rem;
            font-weight: 700;
            color: #00e5cc;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.75rem;
            color: #7b8fa8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* ── Expanders ───────────────────────────────────────────────── */
        details summary {
            color: #9eb3cc;
            font-size: 0.88rem;
            font-weight: 500;
        }
        details[open] summary {
            color: #00bfa5;
        }

        /* ── Dividers ────────────────────────────────────────────────── */
        hr {
            border-color: #1e2a3a;
        }

        /* ── Captions / small text ───────────────────────────────────── */
        .stCaption, small {
            color: #5c7288 !important;
        }

        /* ── Login card ──────────────────────────────────────────────── */
        .login-card {
            background: #141920;
            border: 1px solid #1e2a3a;
            border-radius: 16px;
            padding: 2.5rem 2rem 2rem;
            margin-top: 4rem;
            box-shadow: 0 8px 40px rgba(0,0,0,0.4);
        }
        .login-title {
            font-size: 2rem;
            font-weight: 700;
            color: #e8f0fe;
            margin-bottom: 0.25rem;
        }
        .login-sub {
            font-size: 0.875rem;
            color: #5c7288;
            margin-bottom: 1.5rem;
        }
        .accent { color: #00bfa5; }

        /* ── Dataframe / table ───────────────────────────────────────── */
        [data-testid="stDataFrame"] {
            border-radius: 8px;
            overflow: hidden;
        }

        /* ── Spinner ─────────────────────────────────────────────────── */
        .stSpinner > div {
            border-top-color: #00bfa5 !important;
        }

        /* ── Sticky chat input bar (bottom white strip) ──────────────── */
        [data-testid="stBottom"] {
            background-color: #0e1117;
            border-top: 1px solid #1e2a3a;
        }
        [data-testid="stBottom"] > div {
            background-color: #0e1117;
        }

        /* ── Scrollbar ───────────────────────────────────────────────── */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0e1117; }
        ::-webkit-scrollbar-thumb { background: #2a3a50; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #00bfa5; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CSV_PATH = os.path.join(_ROOT, "data", "processed", "cleaned_courses.csv")
CATEGORIES = ["Business", "Computer Science", "Data Science"]
DIFFICULTY_ORDER = ["Beginner", "Intermediate", "Advanced", "Mixed"]
LEVEL_COLORS = {
    "Beginner": "#4CAF50",
    "Intermediate": "#2196F3",
    "Advanced": "#FF5722",
    "Mixed": "#9C27B0",
}

# ---------------------------------------------------------------------------
# Regex patterns — match tool output text to trigger chart rendering
# ---------------------------------------------------------------------------

# create_learning_path outputs "--- Timeline (N hrs/week) ---"
TIMELINE_TRIGGER_RE = re.compile(r"---\s*Timeline", re.IGNORECASE)

# Matches lines like: "  Weeks 1–16: Beginner (3 courses, ~160 hrs)"
# Also handles en-dash (–) and regular hyphen (-), and the colon vs space separator
TIMELINE_ROW_RE = re.compile(
    r"Weeks?\s+(\d+)\s*[–\-]\s*(\d+)\s*[:\s]+(\w+)\s*"
    r"\(\d+\s*courses?,\s*~(\d+)\s*hrs?\)",
    re.IGNORECASE,
)

# analyze_skill_gap outputs "Skill Gap Analysis" header
SKILL_GAP_TRIGGER_RE = re.compile(r"Skill\s+Gap\s+Analysis", re.IGNORECASE)

# Matches "  Completion: 65%" or "  Completion: 65.3%"
COMPLETION_RE = re.compile(r"Completion:\s*(\d+(?:\.\d+)?)\s*%", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def init_session_state() -> None:
    """Initialize all session_state keys with safe defaults on first run."""
    defaults = {
        "user_id": None,   # str | None — gates the login screen
        "agent": None,     # CourseAdvisorAgent | None
        "messages": [],    # List[{role, content, chart_data}]
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ---------------------------------------------------------------------------
# Data loader (cached across reruns)
# ---------------------------------------------------------------------------

@st.cache_data
def load_courses() -> pd.DataFrame:
    """Load and cache the cleaned Coursera CSV. Called once per process."""
    df = pd.read_csv(CSV_PATH)
    df["course_rating"] = pd.to_numeric(df["course_rating"], errors="coerce")
    df["estimated_hours"] = pd.to_numeric(df["estimated_hours"], errors="coerce")
    df["difficulty_level"] = df["difficulty_level"].str.strip()
    df["category"] = df["category"].str.strip()
    return df


# ---------------------------------------------------------------------------
# Login screen
# ---------------------------------------------------------------------------

def render_login_screen() -> str | None:
    """
    Show a centered login card. Returns the entered username on submit,
    None if the user hasn't submitted yet.
    """
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div class="login-card">
                <div class="login-title">Course <span class="accent">Advisor</span></div>
                <div class="login-sub">AI-powered learning path planner &mdash; Coursera × LLM</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        username = st.text_input(
            "Username",
            key="login_input",
            placeholder="e.g. alice",
            label_visibility="collapsed",
        )
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        if st.button("Start Learning →", type="primary", use_container_width=True):
            name = username.strip()
            if name:
                return name
            st.warning("Please enter a username.")
    return None


# ---------------------------------------------------------------------------
# Sidebar — profile cards
# ---------------------------------------------------------------------------

def _render_profile_cards(agent: CourseAdvisorAgent) -> None:
    """Display current profile: skill tags, goal, and metric cards."""
    profile = agent.get_profile()

    skills = profile.get("known_skills", [])
    if skills:
        tags = " · ".join(f"`{s}`" for s in skills)
        st.markdown(f"**Skills:** {tags}")
    else:
        st.caption("No skills recorded yet.")

    goal = profile.get("goals") or ""
    st.markdown(f"**Goal:** {goal if goal else '_Not set_'}")

    col1, col2 = st.columns(2)
    with col1:
        hrs = profile.get("hours_per_week") or 10.0
        st.metric("Hrs / Week", int(hrs))
    with col2:
        diff = profile.get("preferred_difficulty") or "Any"
        st.metric("Level", diff)


# ---------------------------------------------------------------------------
# Sidebar — profile edit forms
# ---------------------------------------------------------------------------

def _render_edit_forms(agent: CourseAdvisorAgent) -> None:
    """Three expanders for editing skills, goal, and hours/week."""

    with st.expander("Add Skills"):
        new_skills_raw = st.text_input(
            "Skills (comma-separated)",
            key="input_add_skills",
            placeholder="e.g. Python, SQL, Machine Learning",
        )
        if st.button("Save Skills", key="btn_save_skills"):
            skills_list = [s.strip() for s in new_skills_raw.split(",") if s.strip()]
            if skills_list:
                agent.add_skills(skills_list)
                st.success(f"Added {len(skills_list)} skill(s).")
                st.rerun()
            else:
                st.warning("Enter at least one skill.")

    with st.expander("Set Goal"):
        new_goal = st.text_input(
            "Your learning goal",
            key="input_set_goal",
            placeholder="e.g. Become a data scientist",
        )
        if st.button("Save Goal", key="btn_save_goal"):
            if new_goal.strip():
                agent.update_profile(goals=new_goal.strip())
                st.rerun()
            else:
                st.warning("Goal cannot be empty.")

    with st.expander("Set Hours / Week"):
        new_hours = st.number_input(
            "Available study hours per week",
            min_value=1.0,
            max_value=80.0,
            value=float(agent.get_profile().get("hours_per_week") or 10.0),
            step=0.5,
            key="input_set_hours",
        )
        if st.button("Save Hours", key="btn_save_hours"):
            agent.update_profile(hours_per_week=float(new_hours))
            st.rerun()


# ---------------------------------------------------------------------------
# Sidebar — quick actions (prefill chat messages)
# ---------------------------------------------------------------------------

def _enqueue_user_message(content: str) -> None:
    """Append a user message to the chat history and trigger rerun."""
    st.session_state["messages"].append({
        "role": "user",
        "content": content,
        "chart_data": None,
    })
    st.rerun()


def _render_quick_actions() -> None:
    """
    Sidebar quick-action forms. Each form constructs a natural-language
    message and injects it into the chat so the agent processes it normally.
    """
    st.subheader("Quick Actions")

    with st.expander("Build Learning Path"):
        qa_goal = st.text_input(
            "Learning goal",
            key="qa_lp_goal",
            placeholder="e.g. Become a data analyst",
        )
        qa_hours = st.number_input(
            "Hours / week",
            min_value=1.0,
            max_value=80.0,
            value=10.0,
            step=0.5,
            key="qa_lp_hours",
        )
        if st.button("Generate Path", key="btn_gen_path"):
            if qa_goal.strip():
                msg = (
                    f"Create a learning path for my goal: '{qa_goal.strip()}' "
                    f"with {int(qa_hours)} hours per week available to study."
                )
                _enqueue_user_message(msg)
            else:
                st.warning("Please enter a goal.")

    with st.expander("Skill Gap Analysis"):
        qa_target = st.text_input(
            "Target role or goal",
            key="qa_gap_target",
            placeholder="e.g. Machine Learning Engineer",
        )
        qa_current = st.text_input(
            "Your current skills (comma-separated)",
            key="qa_gap_current",
            placeholder="e.g. Python, Excel",
        )
        if st.button("Analyze Gap", key="btn_gap"):
            if qa_target.strip():
                current_part = (
                    f"My current skills are: {qa_current.strip()}."
                    if qa_current.strip()
                    else "I have no relevant skills yet."
                )
                msg = (
                    f"Analyze my skill gap for becoming a {qa_target.strip()}. "
                    f"{current_part}"
                )
                _enqueue_user_message(msg)
            else:
                st.warning("Please enter a target role or goal.")


# ---------------------------------------------------------------------------
# Sidebar — course catalog explorer
# ---------------------------------------------------------------------------

def _render_course_explorer() -> None:
    """Filterable course catalog table loaded from the cleaned CSV."""
    with st.expander("Browse Courses", expanded=False):
        df = load_courses()

        selected_cats = st.multiselect(
            "Category",
            CATEGORIES,
            default=CATEGORIES,
            key="explorer_cats",
        )
        selected_diffs = st.multiselect(
            "Difficulty",
            DIFFICULTY_ORDER,
            default=DIFFICULTY_ORDER,
            key="explorer_diffs",
        )
        min_rating = st.slider(
            "Min Rating",
            min_value=0.0,
            max_value=5.0,
            value=3.0,
            step=0.1,
            key="explorer_rating",
        )

        mask = (
            df["category"].isin(selected_cats)
            & df["difficulty_level"].isin(selected_diffs)
            & (df["course_rating"] >= min_rating)
        )
        filtered = df[mask]

        st.caption(f"{len(filtered):,} of {len(df):,} courses")
        st.dataframe(
            filtered[
                [
                    "course_name",
                    "university",
                    "difficulty_level",
                    "course_rating",
                    "category",
                    "estimated_hours",
                ]
            ].rename(
                columns={
                    "course_name": "Course",
                    "university": "University",
                    "difficulty_level": "Level",
                    "course_rating": "Rating",
                    "category": "Category",
                    "estimated_hours": "Est. Hours",
                }
            ),
            use_container_width=True,
            hide_index=True,
            height=300,
        )


# ---------------------------------------------------------------------------
# Sidebar — top-level orchestrator
# ---------------------------------------------------------------------------

def render_sidebar(agent: CourseAdvisorAgent) -> None:
    """Render the full sidebar: profile, edit forms, quick actions, explorer."""
    with st.sidebar:
        uid = st.session_state["user_id"]
        initials = uid[:2].upper()
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:0.75rem;padding:0.25rem 0 0.75rem;">
                <div style="width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,#00bfa5,#0097a7);
                            display:flex;align-items:center;justify-content:center;
                            font-weight:700;font-size:0.9rem;color:#fff;flex-shrink:0;">{initials}</div>
                <div>
                    <div style="font-weight:600;color:#e0e6ef;line-height:1.2">{uid}</div>
                    <div style="font-size:0.73rem;color:#5c7288">Learning Profile</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _render_profile_cards(agent)
        st.divider()
        _render_edit_forms(agent)
        st.divider()
        _render_quick_actions()
        st.divider()
        _render_course_explorer()
        st.divider()
        if st.button("🔄 Reset Chat", key="btn_reset"):
            agent.reset()
            st.session_state["messages"] = []
            st.rerun()


# ---------------------------------------------------------------------------
# Chart parsing
# ---------------------------------------------------------------------------

def _extract_chart_data(response: str) -> dict | None:
    """
    Parse the agent's text response for chart-triggering patterns.

    Returns a typed dict for the chart renderer, or None if no chart applies.
    """
    # --- Timeline chart ---
    if TIMELINE_TRIGGER_RE.search(response):
        rows = []
        for m in TIMELINE_ROW_RE.finditer(response):
            rows.append({
                "week_start": int(m.group(1)),
                "week_end": int(m.group(2)),
                "level": m.group(3).strip().capitalize(),
                "hours": int(m.group(4)),
            })
        if rows:
            return {"type": "timeline", "rows": rows}

    # --- Skill gap donut ---
    if SKILL_GAP_TRIGGER_RE.search(response):
        pct_m = COMPLETION_RE.search(response)
        if pct_m:
            return {"type": "skill_gap", "completion": float(pct_m.group(1))}

    return None


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------

def _render_chart(chart_data: dict) -> None:
    """Dispatch to the appropriate chart renderer."""
    if chart_data["type"] == "timeline":
        _render_timeline_chart(chart_data["rows"])
    elif chart_data["type"] == "skill_gap":
        _render_skill_gap_chart(chart_data["completion"])


def _render_timeline_chart(rows: list) -> None:
    """
    Horizontal Gantt-style bar chart showing the learning path timeline.
    Each difficulty level is one horizontal bar spanning its week range.
    """
    fig = go.Figure()

    for row in rows:
        duration = row["week_end"] - row["week_start"] + 1
        color = LEVEL_COLORS.get(row["level"], "#607D8B")
        fig.add_trace(
            go.Bar(
                x=[duration],
                y=[row["level"]],
                base=[row["week_start"] - 1],  # offset creates Gantt effect
                orientation="h",
                marker_color=color,
                name=row["level"],
                text=f"Wks {row['week_start']}–{row['week_end']}  ~{row['hours']} hrs",
                textposition="inside",
                insidetextanchor="middle",
                hovertemplate=(
                    f"<b>{row['level']}</b><br>"
                    f"Weeks {row['week_start']}–{row['week_end']}<br>"
                    f"~{row['hours']} hours<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(text="Learning Path Timeline", font=dict(color="#e0e6ef", size=14)),
        xaxis_title="Week",
        yaxis=dict(categoryorder="array", categoryarray=list(reversed(DIFFICULTY_ORDER))),
        barmode="overlay",
        showlegend=False,
        height=280,
        margin=dict(l=10, r=10, t=40, b=30),
        paper_bgcolor="#141920",
        plot_bgcolor="#141920",
        font=dict(color="#9eb3cc"),
        xaxis=dict(gridcolor="#1e2a3a", zerolinecolor="#1e2a3a"),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_skill_gap_chart(completion: float) -> None:
    """
    Donut chart showing how much of the skill gap has already been covered.
    Center annotation displays the completion percentage.
    """
    gap = max(0.0, 100.0 - completion)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Skills Matched", "Gap Remaining"],
                values=[completion, gap],
                hole=0.55,
                marker_colors=["#4CAF50", "#ECEFF1"],
                textinfo="label+percent",
                hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
            )
        ]
    )
    fig.add_annotation(
        text=f"{completion:.0f}%",
        x=0.5,
        y=0.5,
        font_size=26,
        showarrow=False,
    )
    fig.update_layout(
        title=dict(text="Skill Gap Coverage", font=dict(color="#e0e6ef", size=14)),
        showlegend=True,
        height=280,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="#141920",
        plot_bgcolor="#141920",
        font=dict(color="#9eb3cc"),
        legend=dict(bgcolor="#141920", bordercolor="#1e2a3a"),
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Chat panel
# ---------------------------------------------------------------------------

def _render_message_history() -> None:
    """Render all past messages as chat bubbles. Charts appear below assistant replies."""
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("chart_data"):
                _render_chart(msg["chart_data"])


def _process_pending_message(agent: CourseAdvisorAgent) -> None:
    """
    If the last message is from the user and has no agent reply yet,
    call the agent and append the assistant response.

    Calls st.rerun() after appending — safe because on re-entry the last
    message is now 'assistant' role so this function exits immediately.
    """
    msgs = st.session_state["messages"]
    if not msgs or msgs[-1]["role"] != "user":
        return

    user_content = msgs[-1]["content"]

    with st.spinner("Thinking..."):
        try:
            response = agent.chat(user_content)
        except Exception as e:
            response = f"Sorry, something went wrong: {e}"

    chart_data = _extract_chart_data(response)
    msgs.append({
        "role": "assistant",
        "content": response,
        "chart_data": chart_data,
    })
    st.rerun()


def _render_chat_input() -> None:
    """Capture new user input from the pinned chat input box."""
    user_input = st.chat_input("Ask about courses, skills, or your learning path...")
    if user_input and user_input.strip():
        st.session_state["messages"].append({
            "role": "user",
            "content": user_input.strip(),
            "chart_data": None,
        })
        st.rerun()


def render_chat_panel(agent: CourseAdvisorAgent) -> None:
    """Main panel: chat history, pending message processing, and chat input."""
    st.markdown(
        "<h2 style='font-weight:700;color:#e8f0fe;margin-bottom:0.25rem'>Chat with Your "
        "<span style='color:#00bfa5'>Advisor</span></h2>",
        unsafe_allow_html=True,
    )
    _render_message_history()
    _process_pending_message(agent)
    _render_chat_input()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Course Advisor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

_apply_theme()
init_session_state()

# Login gate — halt rendering until a user_id is set
if st.session_state["user_id"] is None:
    result = render_login_screen()
    if result:
        st.session_state["user_id"] = result
        st.rerun()
    st.stop()

# Agent init — created once per browser session, stored in session_state
if st.session_state["agent"] is None:
    with st.spinner("Loading your profile and tools..."):
        st.session_state["agent"] = CourseAdvisorAgent(
            user_id=st.session_state["user_id"]
        )

agent = st.session_state["agent"]

render_sidebar(agent)
render_chat_panel(agent)
