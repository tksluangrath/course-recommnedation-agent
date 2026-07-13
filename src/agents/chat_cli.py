"""
CLI Chat Interface for Course Advisor Agent

Terminal-based chat loop with user profile persistence.
Profiles are saved to SQLite and loaded on startup by username.

Usage:
    python src/agents/chat_cli.py
    python src/agents/chat_cli.py --user alice
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent))

from course_advisor import CourseAdvisorAgent


WELCOME = """
============================================================
  Course Advisor - AI Learning Path Planner
============================================================

  I can help you with:
  - Finding courses on any topic
  - Building personalized learning paths with time estimates
  - Recommending courses based on skills you want
  - Analyzing skill gaps (foundational skills first)
  - Showing prerequisite chains for specific courses
  - Discovering trending skills

  Profile commands:
  /profile          - Show your saved profile
  /skills A, B, C  - Add skills to your profile
  /goal <text>      - Set your learning goal
  /hours <n>        - Set available study hours/week

  Session commands:
  /reset            - Clear conversation history
  /history          - Show conversation history
  /quit             - Exit

============================================================
"""


def _prompt_username() -> str:
    """Prompt for a username at startup."""
    print("Enter your username (or press Enter to use 'guest'):")
    try:
        name = input("  Username: ").strip()
    except (KeyboardInterrupt, EOFError):
        return "guest"
    return name if name else "guest"


def _show_greeting(agent: CourseAdvisorAgent) -> None:
    """Show a personalized greeting based on the user's profile."""
    profile = agent.get_profile()
    skills = profile.get('known_skills', [])
    goal = profile.get('goals', '').strip()
    hrs = profile.get('hours_per_week', 10.0)

    if skills or goal:
        print(f"\nWelcome back, {profile['user_id']}!")
        if goal:
            print(f"  Goal       : {goal}")
        if skills:
            print(f"  Skills     : {', '.join(skills[:8])}{'...' if len(skills) > 8 else ''}")
        print(f"  Study time : {int(hrs)} hrs/week")
        print()
    else:
        print(f"\nHello, {profile['user_id']}! Your profile is empty — use /skills, /goal, and /hours to set it up.\n")


def _handle_command(cmd: str, agent: CourseAdvisorAgent) -> bool:
    """Handle a slash command. Returns True if handled, False if not a command."""
    lower = cmd.lower().strip()

    if lower == "/quit":
        profile = agent.get_profile()
        print(f"\nSaving profile for {profile['user_id']}...")
        print(agent.display_profile())
        print("\nGoodbye!")
        sys.exit(0)

    elif lower == "/reset":
        agent.reset()
        print("Conversation history cleared.\n")

    elif lower == "/history":
        messages = agent.get_history()
        if not messages:
            print("No conversation history yet.\n")
        else:
            print("\n--- Conversation History ---")
            for msg in messages:
                role = getattr(msg, 'type', 'unknown').capitalize()
                content = msg.content[:300] + ('...' if len(msg.content) > 300 else '')
                print(f"{role}: {content}")
            print("--- End History ---\n")

    elif lower == "/profile":
        print()
        print(agent.display_profile())
        print()

    elif lower.startswith("/skills "):
        raw = cmd[len("/skills "):].strip()
        new_skills = [s.strip() for s in raw.split(",") if s.strip()]
        if not new_skills:
            print("Usage: /skills Python, SQL, Machine Learning\n")
        else:
            updated = agent.add_skills(new_skills)
            print(f"Skills updated: {', '.join(updated)}\n")

    elif lower.startswith("/goal "):
        goal_text = cmd[len("/goal "):].strip()
        if goal_text:
            agent.update_profile(goals=goal_text)
            print(f"Goal set: {goal_text}\n")
        else:
            print("Usage: /goal become a machine learning engineer\n")

    elif lower.startswith("/hours "):
        hours_str = cmd[len("/hours "):].strip()
        try:
            hours = float(hours_str)
            if hours <= 0:
                raise ValueError
            agent.update_profile(hours_per_week=hours)
            print(f"Study time set to {int(hours)} hours/week. Timelines will update automatically.\n")
        except ValueError:
            print("Usage: /hours 8   (positive number)\n")

    else:
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Course Advisor CLI")
    parser.add_argument("--user", type=str, default=None, help="Username for profile persistence")
    args = parser.parse_args()

    print(WELCOME)

    # Resolve username
    user_id = args.user or _prompt_username()

    try:
        agent = CourseAdvisorAgent(user_id=user_id)
    except Exception as e:
        print(f"\nFailed to initialize agent: {e}")
        print("\nMake sure Ollama is running: ollama serve")
        print("And the model is downloaded: ollama pull llama3.1")
        return

    _show_greeting(agent)
    print("Type your message below. Use /quit to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        # Handle slash commands first
        if user_input.startswith("/"):
            _handle_command(user_input, agent)
            continue

        # Get streamed response from agent
        print()
        print("Advisor: ", end="", flush=True)
        for chunk in agent.stream_chat(user_input):
            print(chunk, end="", flush=True)
        print("\n")


if __name__ == "__main__":
    main()
