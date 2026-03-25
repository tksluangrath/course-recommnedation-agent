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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

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
            background-color: #080c12;
        }

        /* ── Main content column ─────────────────────────────────────── */
        .main .block-container {
            padding-top: 1.5rem;
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 900px;
        }

        /* ── Sidebar ─────────────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background-color: #0d1117;
            border-right: 1px solid #1a2236;
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: #e0e6ef;
        }

        /* ── Primary buttons ─────────────────────────────────────────── */
        .stButton > button[kind="primary"],
        .stButton > button[data-testid*="primary"] {
            background: linear-gradient(135deg, #00c9a7, #0097a7);
            color: #fff;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.9rem;
            letter-spacing: 0.3px;
            padding: 0.55rem 1.25rem;
            transition: all 0.2s ease;
            box-shadow: 0 2px 12px rgba(0,201,167,0.25);
        }
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 20px rgba(0,201,167,0.35);
        }

        /* ── Secondary buttons ───────────────────────────────────────── */
        .stButton > button {
            border-radius: 10px;
            border: 1px solid #1e2d42;
            background-color: #111827;
            color: #b0c4de;
            font-size: 0.875rem;
            transition: all 0.15s ease;
        }
        .stButton > button:hover {
            border-color: #00bfa5;
            color: #00e5cc;
            background-color: rgba(0,191,165,0.06);
        }

        /* ── Chat messages ───────────────────────────────────────────── */
        .stChatMessage {
            border-radius: 14px;
            padding: 6px 0;
        }
        /* User message bubble */
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            background: linear-gradient(135deg, rgba(0,191,165,0.08), rgba(0,151,167,0.06));
            border: 1px solid rgba(0,191,165,0.12);
            border-radius: 14px;
            padding: 0.25rem 0.5rem;
            margin: 0.25rem 0;
        }
        /* Assistant message bubble */
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 14px;
            padding: 0.25rem 0.5rem;
            margin: 0.25rem 0;
        }
        [data-testid="stChatMessageContent"] p {
            line-height: 1.75;
            color: #cdd9ea;
        }

        /* ── Chat input ──────────────────────────────────────────────── */
        .stChatInputContainer,
        .stChatInputContainer > div,
        [data-testid="stChatInput"],
        [data-testid="stChatInput"] > div {
            background-color: #080c12 !important;
        }
        .stChatInputContainer textarea,
        [data-testid="stChatInput"] textarea {
            background-color: #0f1823 !important;
            border: 1px solid #1e2d42 !important;
            border-radius: 14px !important;
            color: #d4dcea !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.9rem !important;
            padding: 0.75rem 1rem !important;
        }
        .stChatInputContainer textarea:focus,
        [data-testid="stChatInput"] textarea:focus {
            border-color: #00bfa5 !important;
            box-shadow: 0 0 0 3px rgba(0,191,165,0.12) !important;
        }
        .stChatInputContainer textarea::placeholder,
        [data-testid="stChatInput"] textarea::placeholder {
            color: #3d5066 !important;
        }

        /* ── Text inputs + labels ─────────────────────────────────────── */
        .stTextInput input, .stNumberInput input {
            background-color: #0f1823 !important;
            border: 1px solid #1e2d42 !important;
            border-radius: 10px !important;
            color: #d4dcea !important;
            font-family: 'Inter', sans-serif !important;
        }
        .stTextInput input:focus, .stNumberInput input:focus {
            border-color: #00bfa5 !important;
            box-shadow: 0 0 0 2px rgba(0,191,165,0.15) !important;
        }
        .stTextInput input::placeholder, .stNumberInput input::placeholder {
            color: #3d5066 !important;
        }
        /* Widget labels */
        [data-testid="stWidgetLabel"] p,
        .stTextInput label, .stNumberInput label,
        .stSlider label, .stMultiSelect label {
            color: #6e8aaa !important;
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.4px !important;
        }
        /* General paragraph text in sidebar */
        section[data-testid="stSidebar"] p {
            color: #8fa8c0;
        }

        /* ── Metric cards ────────────────────────────────────────────── */
        [data-testid="stMetric"] {
            background: rgba(0,191,165,0.05);
            border: 1px solid rgba(0,191,165,0.1);
            border-radius: 10px;
            padding: 0.5rem 0.75rem;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.5rem;
            font-weight: 700;
            color: #00e5cc;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.72rem;
            color: #5c7a94;
            text-transform: uppercase;
            letter-spacing: 0.6px;
        }

        /* ── Expanders ───────────────────────────────────────────────── */
        details {
            background: rgba(255,255,255,0.02);
            border: 1px solid #1a2638 !important;
            border-radius: 10px !important;
            margin-bottom: 0.4rem;
        }
        details summary {
            color: #8fa8c0;
            font-size: 0.875rem;
            font-weight: 500;
            padding: 0.25rem 0.1rem;
        }
        details[open] summary {
            color: #00c9a7;
        }

        /* ── Dividers ────────────────────────────────────────────────── */
        hr {
            border-color: #131e2e;
        }

        /* ── Captions / small text ───────────────────────────────────── */
        .stCaption, small {
            color: #4a6278 !important;
        }

        /* ── Login screen ────────────────────────────────────────────── */
        .login-wrapper {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 60vh;
            padding: 2rem 0;
        }
        .login-logo {
            width: 64px;
            height: 64px;
            border-radius: 18px;
            background: linear-gradient(135deg, #00c9a7 0%, #0076a8 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            margin: 0 auto 1.5rem;
            box-shadow: 0 8px 30px rgba(0,201,167,0.3);
        }
        .login-card {
            background: linear-gradient(160deg, #0f1823 0%, #0b1219 100%);
            border: 1px solid #1a2638;
            border-radius: 20px;
            padding: 2.75rem 2.5rem 2.25rem;
            margin-top: 2rem;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(0,191,165,0.05);
            text-align: center;
        }
        .login-title {
            font-size: 2.1rem;
            font-weight: 800;
            color: #eaf0fb;
            margin-bottom: 0.35rem;
            letter-spacing: -0.5px;
        }
        .login-sub {
            font-size: 0.9rem;
            color: #4a6278;
            margin-bottom: 0;
            line-height: 1.5;
        }
        .login-divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, #1a2638, transparent);
            margin: 1.5rem 0;
        }
        .accent { color: #00c9a7; }

        /* ── Welcome / empty state ───────────────────────────────────── */
        .welcome-hero {
            text-align: center;
            padding: 3rem 1rem 2rem;
        }
        .welcome-icon {
            width: 72px;
            height: 72px;
            border-radius: 20px;
            background: linear-gradient(135deg, #00c9a7, #0076a8);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.25rem;
            margin: 0 auto 1.25rem;
            box-shadow: 0 8px 32px rgba(0,201,167,0.25);
        }
        .welcome-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: #eaf0fb;
            margin-bottom: 0.5rem;
            letter-spacing: -0.3px;
        }
        .welcome-sub {
            font-size: 0.95rem;
            color: #4a6278;
            max-width: 480px;
            margin: 0 auto 2.5rem;
            line-height: 1.6;
        }
        .prompt-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.75rem;
            max-width: 620px;
            margin: 0 auto;
        }
        .prompt-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid #1a2638;
            border-radius: 12px;
            padding: 1rem 1.1rem;
            text-align: left;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .prompt-card:hover {
            border-color: rgba(0,191,165,0.35);
            background: rgba(0,191,165,0.05);
            transform: translateY(-1px);
        }
        .prompt-card-label {
            font-size: 0.72rem;
            font-weight: 600;
            color: #00bfa5;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.3rem;
        }
        .prompt-card-text {
            font-size: 0.875rem;
            color: #8fa8c0;
            line-height: 1.4;
        }

        /* ── Chat panel header ───────────────────────────────────────── */
        .chat-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.25rem 0 1.25rem;
            border-bottom: 1px solid #131e2e;
            margin-bottom: 1rem;
        }
        .chat-header-icon {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            background: linear-gradient(135deg, #00c9a7, #0076a8);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            flex-shrink: 0;
        }
        .chat-header-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #eaf0fb;
            margin: 0;
        }
        .chat-header-sub {
            font-size: 0.78rem;
            color: #4a6278;
            margin: 0;
        }
        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #00c9a7;
            display: inline-block;
            margin-right: 4px;
            box-shadow: 0 0 6px rgba(0,201,167,0.7);
            animation: pulse-dot 2s ease-in-out infinite;
        }
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        /* ── Sidebar section headers ─────────────────────────────────── */
        .sidebar-section-label {
            font-size: 0.68rem;
            font-weight: 700;
            color: #3d5470;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin: 0.75rem 0 0.4rem;
        }

        /* ── Dataframe / table ───────────────────────────────────────── */
        [data-testid="stDataFrame"] {
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #1a2638;
        }

        /* ── Spinner ─────────────────────────────────────────────────── */
        .stSpinner > div {
            border-top-color: #00bfa5 !important;
        }

        /* ── Sticky chat input bar ───────────────────────────────────── */
        [data-testid="stBottom"] {
            background-color: #080c12;
            border-top: 1px solid #131e2e;
        }
        [data-testid="stBottom"] > div {
            background-color: #080c12;
        }

        /* ── Scrollbar ───────────────────────────────────────────────── */
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1e2d42; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #00bfa5; }

        /* ── Multiselect tags ────────────────────────────────────────── */
        [data-testid="stMultiSelect"] span[data-baseweb="tag"] {
            background-color: rgba(0,191,165,0.15) !important;
            border: 1px solid rgba(0,191,165,0.25) !important;
            color: #00c9a7 !important;
            border-radius: 6px !important;
        }

        /* ── Slider ──────────────────────────────────────────────────── */
        [data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {
            background-color: #00c9a7 !important;
            border-color: #00c9a7 !important;
        }
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
    col1, col2, col3 = st.columns([1, 1.6, 1])
    with col2:
        st.markdown(
            """
            <div style="text-align:center;padding-top:3rem;">
                <div class="login-logo">🎓</div>
            </div>
            <div class="login-card">
                <div class="login-title">Course <span class="accent">Advisor</span></div>
                <div class="login-sub">
                    AI-powered learning path planner<br>
                    built on Coursera &amp; LLMs
                </div>
                <div class="login-divider"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        username = st.text_input(
            "Username",
            key="login_input",
            placeholder="Enter your username to get started",
            label_visibility="collapsed",
        )
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        if st.button("Start Learning →", type="primary", use_container_width=True):
            name = username.strip()
            if name:
                return name
            st.warning("Please enter a username.")
        st.markdown(
            "<p style='text-align:center;font-size:0.75rem;color:#2e4055;margin-top:1rem'>"
            "No account needed — just pick a username</p>",
            unsafe_allow_html=True,
        )
    return None


# ---------------------------------------------------------------------------
# Sidebar — profile cards
# ---------------------------------------------------------------------------

def _render_profile_cards(agent: CourseAdvisorAgent) -> None:
    """Display current profile: skill tags, goal, and metric cards."""
    profile = agent.get_profile()

    st.markdown("<div class='sidebar-section-label'>Profile</div>", unsafe_allow_html=True)

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
            <div style="display:flex;align-items:center;gap:0.85rem;padding:0.5rem 0 1rem;">
                <div style="width:42px;height:42px;border-radius:12px;
                            background:linear-gradient(135deg,#00c9a7,#0076a8);
                            display:flex;align-items:center;justify-content:center;
                            font-weight:700;font-size:0.95rem;color:#fff;flex-shrink:0;
                            box-shadow:0 4px 14px rgba(0,201,167,0.3);">{initials}</div>
                <div>
                    <div style="font-weight:600;color:#e8f0fe;line-height:1.2;font-size:0.95rem">{uid}</div>
                    <div style="font-size:0.72rem;color:#3d5470;margin-top:1px">
                        <span class="status-dot"></span>Active learner
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _render_profile_cards(agent)
        st.markdown("<div class='sidebar-section-label'>Edit Profile</div>", unsafe_allow_html=True)
        _render_edit_forms(agent)
        st.markdown("<div class='sidebar-section-label'>Quick Actions</div>", unsafe_allow_html=True)
        _render_quick_actions()
        st.markdown("<div class='sidebar-section-label'>Course Catalog</div>", unsafe_allow_html=True)
        _render_course_explorer()
        st.divider()
        if st.button("↺  Reset Chat", key="btn_reset"):
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
        paper_bgcolor="#080c12",
        plot_bgcolor="#080c12",
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
        paper_bgcolor="#080c12",
        plot_bgcolor="#080c12",
        font=dict(color="#9eb3cc"),
        legend=dict(bgcolor="#080c12", bordercolor="#1a2638"),
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


_STARTER_PROMPTS = [
    ("Learning Path", "Recommend courses", "Build me a learning path to become a data scientist with 10 hrs/week"),
    ("Skill Gap", "Find what's missing", "Analyze my skill gap for becoming a machine learning engineer"),
    ("Top Picks", "Discover courses", "What are the highest-rated beginner-friendly Python courses?"),
    ("Career Move", "Plan your pivot", "I want to transition from marketing to product management — what should I study?"),
]


def _render_empty_state() -> None:
    """Welcome hero + suggested prompt cards shown when no messages exist."""
    st.markdown(
        """
        <div class="welcome-hero">
            <div class="welcome-icon">🎓</div>
            <div class="welcome-title">Your AI Course Advisor</div>
            <div class="welcome-sub">
                Ask me anything about learning paths, skill gaps, or course recommendations.
                I'll help you build a personalized curriculum from thousands of Coursera courses.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    for i, (label, title, prompt) in enumerate(_STARTER_PROMPTS):
        with cols[i % 2]:
            if st.button(
                f"**{title}**\n\n{prompt[:60]}{'…' if len(prompt) > 60 else ''}",
                key=f"starter_{i}",
                use_container_width=True,
            ):
                st.session_state["messages"].append({
                    "role": "user",
                    "content": prompt,
                    "chart_data": None,
                })
                st.rerun()

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)


def render_chat_panel(agent: CourseAdvisorAgent) -> None:
    """Main panel: header, empty state or chat history, and chat input."""
    st.markdown(
        """
        <div class="chat-header">
            <div class="chat-header-icon">🤖</div>
            <div>
                <div class="chat-header-title">Course Advisor</div>
                <div class="chat-header-sub">
                    <span class="status-dot"></span>AI-powered &mdash; Coursera × LLM
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state["messages"]:
        _render_empty_state()
    else:
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
