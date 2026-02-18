"""
CLI Chat Interface for Course Advisor Agent

Simple terminal-based chat loop for interacting with the
course recommendation agent.

Usage:
    python src/agents/chat_cli.py
"""

import sys
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
  - Building personalized learning paths
  - Recommending courses based on skills you want
  - Analyzing skill gaps
  - Discovering trending skills

  Commands:
  /quit    - Exit the chat
  /reset   - Clear conversation history
  /history - Show conversation history

============================================================
"""


def main():
    print(WELCOME)

    try:
        agent = CourseAdvisorAgent()
    except Exception as e:
        print(f"\nFailed to initialize agent: {e}")
        print("\nMake sure Ollama is running: ollama serve")
        print("And the model is downloaded: ollama pull llama3.1")
        return

    print("Type your message below. Use /quit to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        # Handle commands
        if user_input.lower() == "/quit":
            print("\nGoodbye!")
            break
        elif user_input.lower() == "/reset":
            agent.reset()
            print("Conversation reset.\n")
            continue
        elif user_input.lower() == "/history":
            messages = agent.get_history()
            if not messages:
                print("No conversation history yet.\n")
            else:
                print("\n--- Conversation History ---")
                for msg in messages:
                    role = msg.type.capitalize()
                    print(f"{role}: {msg.content[:200]}")
                print("--- End History ---\n")
            continue

        # Get response
        print()
        response = agent.chat(user_input)
        print(f"\nAdvisor: {response}\n")


if __name__ == "__main__":
    main()
