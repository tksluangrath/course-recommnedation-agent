"""
User Profile Manager

Thin wrapper over DatabaseManager for user profile operations.
Handles loading, saving, and updating profiles, and builds the
context string that gets injected into every agent conversation turn.
"""

import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from database import DatabaseManager


class ProfileManager:
    """Manages user profiles backed by SQLite via DatabaseManager."""

    def __init__(self, db: DatabaseManager = None):
        self._db = db or DatabaseManager()

    def load(self, user_id: str) -> dict:
        """Load or create a user profile.

        Returns:
            dict with keys: user_id, known_skills (List[str]), goals (str),
            hours_per_week (float), preferred_difficulty (str|None)
        """
        return self._db.get_or_create_profile(user_id)

    def save(self, user_id: str, profile: dict) -> dict:
        """Write a full profile dict back to the DB.

        known_skills should be a List[str] — serialized automatically.
        """
        return self._db.update_profile(
            user_id,
            known_skills=profile.get('known_skills', []),
            goals=profile.get('goals', ''),
            hours_per_week=profile.get('hours_per_week', 10.0),
            preferred_difficulty=profile.get('preferred_difficulty'),
        )

    def add_skills(self, user_id: str, new_skills: List[str]) -> List[str]:
        """Add skills to the user's profile (deduplicated, case-preserved).

        Returns the updated skills list.
        """
        profile = self.load(user_id)
        existing = {s.lower(): s for s in profile['known_skills']}
        for sk in new_skills:
            key = sk.strip().lower()
            if key and key not in existing:
                existing[key] = sk.strip()
        updated = list(existing.values())
        self._db.update_profile(user_id, known_skills=updated)
        return updated

    def get_context_string(self, user_id: str) -> str:
        """Build a one-line profile summary to inject into the agent conversation.

        Returns empty string if the profile has no meaningful data (new user).

        Example output:
            "User profile — Known skills: Python, SQL | Goal: become a data scientist | 8 hrs/week"
        """
        profile = self.load(user_id)
        parts = []

        skills = profile.get('known_skills', [])
        if skills:
            parts.append(f"Known skills: {', '.join(skills)}")

        goal = profile.get('goals', '').strip()
        if goal:
            parts.append(f"Goal: {goal}")

        hrs = profile.get('hours_per_week')
        if hrs and hrs != 10.0:
            parts.append(f"{int(hrs)} hrs/week available to study")
        elif hrs:
            parts.append(f"{int(hrs)} hrs/week available to study")

        diff = profile.get('preferred_difficulty')
        if diff:
            parts.append(f"Preferred level: {diff}")

        if not parts:
            return ''

        return 'User profile — ' + ' | '.join(parts)

    def format_display(self, user_id: str) -> str:
        """Format profile for display in the CLI /profile command."""
        profile = self.load(user_id)
        lines = [f"Profile: {profile['user_id']}"]
        skills = profile.get('known_skills', [])
        lines.append(f"  Known skills : {', '.join(skills) if skills else '(none set)'}")
        lines.append(f"  Goal         : {profile.get('goals') or '(none set)'}")
        lines.append(f"  Hours/week   : {profile.get('hours_per_week', 10.0)}")
        diff = profile.get('preferred_difficulty')
        lines.append(f"  Pref. level  : {diff or '(any)'}")
        return '\n'.join(lines)


if __name__ == '__main__':
    pm = ProfileManager()

    # Quick smoke test
    user = 'testuser'
    p = pm.load(user)
    print('Loaded:', p)

    skills = pm.add_skills(user, ['Python', 'SQL', 'Statistics'])
    print('After add_skills:', skills)

    pm.save(user, {**p, 'goals': 'become a data scientist', 'hours_per_week': 8.0})
    print('Context:', pm.get_context_string(user))
    print('Display:\n' + pm.format_display(user))
