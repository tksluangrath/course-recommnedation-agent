"""
LangChain Tools for Course Recommendation Agent

Wraps recommender methods as LangChain tools that the AI agent can call.
Each tool accepts string inputs, calls the appropriate recommender, and
returns formatted text for the LLM.
"""

import sys
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
sys.path.insert(0, str(Path(__file__).parent.parent / "recommender"))

from database import DatabaseManager
from content_based import ContentBasedRecommender
from hybrid import HybridRecommender


# Shared instances (initialized lazily)
_db = None
_content_rec = None
_hybrid_rec = None


def _get_db():
    global _db
    if _db is None:
        _db = DatabaseManager()
    return _db


def _get_content_rec():
    global _content_rec
    if _content_rec is None:
        _content_rec = ContentBasedRecommender(_get_db())
    return _content_rec


def _get_hybrid_rec():
    global _hybrid_rec
    if _hybrid_rec is None:
        _hybrid_rec = HybridRecommender()
    return _hybrid_rec


def _format_courses(df, max_courses=5):
    """Format a DataFrame of courses into readable text."""
    if df is None or df.empty:
        return "No courses found."

    lines = []
    for i, (_, row) in enumerate(df.head(max_courses).iterrows(), 1):
        name = row.get('course_name', 'Unknown')
        difficulty = row.get('difficulty_level', '')
        category = row.get('category', '')
        rating = row.get('rating', row.get('course_rating', ''))
        university = row.get('university', '')
        score = row.get('similarity_score', row.get('hybrid_score', row.get('skill_similarity', '')))

        line = f"{i}. {name}"
        details = []
        if difficulty:
            details.append(f"Level: {difficulty}")
        if category:
            details.append(f"Category: {category}")
        if rating:
            details.append(f"Rating: {rating}")
        if university:
            details.append(f"By: {university}")
        if score and isinstance(score, (int, float)):
            details.append(f"Match: {score:.2f}")

        if details:
            line += f"\n   {', '.join(details)}"
        lines.append(line)

    return "\n".join(lines)


@tool
def search_courses(query: str) -> str:
    """Search for courses using a natural language query. Use this when the user asks
    to find courses on a topic, or wants recommendations based on their interests.

    Args:
        query: What the user wants to learn, e.g. 'machine learning', 'web development with React'
    """
    rec = _get_hybrid_rec()
    results = rec.recommend(query, n=5)
    return _format_courses(results)


@tool
def find_similar_courses(course_name: str) -> str:
    """Find courses similar to a specific course. Use this when the user mentions
    a course they liked and wants to find more like it.

    Args:
        course_name: The name of the course to find similar ones for
    """
    rec = _get_content_rec()
    results = rec.recommend_similar(course_name, n=5)
    return _format_courses(results)


@tool
def recommend_by_skills(skills: str) -> str:
    """Recommend courses based on specific skills the user wants to learn.
    Use this when the user lists skills they want to acquire.

    Args:
        skills: Comma-separated list of skills, e.g. 'Python, SQL, Data Analysis'
    """
    skill_list = [s.strip() for s in skills.split(",") if s.strip()]
    if not skill_list:
        return "Please provide at least one skill."

    rec = _get_content_rec()
    results = rec.recommend_by_skills(skill_list, n=5)

    if results.empty:
        return f"No courses found for skills: {', '.join(skill_list)}"

    lines = []
    for i, (_, row) in enumerate(results.head(5).iterrows(), 1):
        matched = row.get('matched_skills', [])
        line = f"{i}. {row['course_name']}"
        details = []
        if row.get('difficulty_level'):
            details.append(f"Level: {row['difficulty_level']}")
        if matched:
            details.append(f"Teaches: {', '.join(matched)}")
        if row.get('skill_match_ratio'):
            details.append(f"Skill coverage: {row['skill_match_ratio']:.0%}")
        if details:
            line += f"\n   {', '.join(details)}"
        lines.append(line)

    return "\n".join(lines)


@tool
def create_learning_path(goal: str, current_skills: str = "") -> str:
    """Create a structured learning path from beginner to advanced for a goal.
    Use this when the user wants a step-by-step learning plan.

    Args:
        goal: The learning goal, e.g. 'become a data scientist', 'learn web development'
        current_skills: Optional comma-separated skills the user already has
    """
    skills = [s.strip() for s in current_skills.split(",") if s.strip()] if current_skills else None

    rec = _get_hybrid_rec()
    path = rec.recommend_learning_path(goal, current_skills=skills, n_per_level=3)

    lines = [f"Learning Path: {goal}\n"]
    for level in ['Beginner', 'Intermediate', 'Advanced']:
        courses = path.get(level)
        lines.append(f"--- {level} ---")
        if courses is not None and not courses.empty:
            for i, (_, row) in enumerate(courses.iterrows(), 1):
                name = row.get('course_name', 'Unknown')
                university = row.get('university', '')
                line = f"  {i}. {name}"
                if university:
                    line += f" (by {university})"
                lines.append(line)
        else:
            lines.append("  No courses found for this level.")
        lines.append("")

    return "\n".join(lines)


@tool
def analyze_skill_gap(goal_skills: str, current_skills: str) -> str:
    """Analyze the gap between a user's current skills and their goal skills.
    Use this when the user wants to know what they need to learn to reach a goal.

    Args:
        goal_skills: Comma-separated skills needed for the goal
        current_skills: Comma-separated skills the user already has
    """
    goal_list = [s.strip() for s in goal_skills.split(",") if s.strip()]
    current_list = [s.strip() for s in current_skills.split(",") if s.strip()]

    if not goal_list:
        return "Please provide goal skills."

    rec = _get_content_rec()
    gap = rec.get_skill_gap(goal_list, current_list)

    lines = [
        f"Skill Gap Analysis",
        f"  Completion: {gap['completion_pct']:.0f}%",
        f"  Skills you have: {', '.join(gap['covered_skills']) or 'None'}",
        f"  Skills to learn: {', '.join(gap['missing_skills']) or 'All covered!'}",
    ]

    recs = gap.get('recommended_courses')
    if recs is not None and not recs.empty:
        lines.append(f"\nRecommended courses to fill the gap:")
        lines.append(_format_courses(recs, max_courses=5))

    return "\n".join(lines)


@tool
def get_course_info(course_name: str) -> str:
    """Get detailed information about a specific course.
    Use this when the user asks about a particular course.

    Args:
        course_name: The name of the course to look up
    """
    db = _get_db()
    courses = db.search_courses(query=course_name, limit=1)

    if not courses:
        return f"Course '{course_name}' not found."

    course = courses[0]
    lines = [
        f"Course: {course.course_name}",
        f"  University: {course.university or 'N/A'}",
        f"  Difficulty: {course.difficulty_level or 'N/A'}",
        f"  Rating: {course.course_rating or 'N/A'}",
        f"  Category: {course.category or 'N/A'}",
        f"  Type: {course.learning_product or 'N/A'}",
        f"  Est. Hours: {course.estimated_hours or 'N/A'}",
        f"  Reviews: {course.num_reviews or 'N/A'}",
    ]

    if course.skills:
        skill_names = [s.name for s in course.skills[:10]]
        lines.append(f"  Skills: {', '.join(skill_names)}")

    if course.course_url:
        lines.append(f"  URL: {course.course_url}")

    return "\n".join(lines)


@tool
def get_popular_skills(category: str = "") -> str:
    """Get the most popular/in-demand skills, optionally filtered by category.
    Use this when the user asks about trending skills or what skills are in demand.

    Args:
        category: Optional category filter, e.g. 'Data Science', 'Computer Science'
    """
    rec = _get_content_rec()
    cat = category.strip() if category.strip() else None
    skills = rec.get_popular_skills(category=cat, top_n=10)

    if not skills:
        return f"No skills data found{f' for category: {cat}' if cat else ''}."

    header = f"Top 10 Skills{f' in {cat}' if cat else ''}:"
    lines = [header]
    for i, s in enumerate(skills, 1):
        lines.append(f"  {i}. {s['skill']} ({s['count']} courses)")

    return "\n".join(lines)


def get_all_tools():
    """Return all available tools for the agent."""
    return [
        search_courses,
        find_similar_courses,
        recommend_by_skills,
        create_learning_path,
        analyze_skill_gap,
        get_course_info,
        get_popular_skills,
    ]
