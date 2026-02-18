"""
Content-Based Recommendation Engine

Recommends courses based on:
1. Semantic similarity (embeddings) - finds courses with similar content
2. Skill overlap - finds courses that teach similar skills
3. Difficulty progression - suggests beginner -> intermediate -> advanced paths
"""

import sys
import ast
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path
from collections import Counter

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))

from database import DatabaseManager
from embeddings import EmbeddingManager


class ContentBasedRecommender:
    """Content-based course recommendation engine."""

    DIFFICULTY_ORDER = {'Beginner': 0, 'Intermediate': 1, 'Advanced': 2, 'Mixed': 1}

    def __init__(self, db: DatabaseManager = None, em: EmbeddingManager = None):
        """Initialize recommender with database and embedding managers."""
        self.db = db or DatabaseManager()
        self.em = em or EmbeddingManager()

        # Load course data for skill-based recommendations
        csv_path = Path("data/processed/cleaned_courses.csv")
        if csv_path.exists():
            self.courses_df = pd.read_csv(csv_path)
            # Parse skills from string representation
            if 'extracted_skills' in self.courses_df.columns:
                self.courses_df['skills_list'] = self.courses_df['extracted_skills'].apply(
                    self._parse_skills
                )
            else:
                self.courses_df['skills_list'] = [[] for _ in range(len(self.courses_df))]
        else:
            self.courses_df = pd.DataFrame()

    @staticmethod
    def _parse_skills(skills_raw) -> List[str]:
        """Parse skills from various formats."""
        if pd.isna(skills_raw):
            return []
        if isinstance(skills_raw, list):
            return skills_raw
        try:
            return ast.literal_eval(str(skills_raw))
        except (ValueError, SyntaxError):
            return [s.strip() for s in str(skills_raw).split(',') if s.strip()]

    def recommend_similar(self, course_name: str, n: int = 10) -> pd.DataFrame:
        """Find courses similar to a given course using semantic search.

        Args:
            course_name: Name of the course to find similar ones for
            n: Number of recommendations

        Returns:
            DataFrame with recommended courses and similarity scores
        """
        results = self.em.search_courses(course_name, n_results=n + 1)

        # Remove the query course itself if it appears in results
        if not results.empty:
            results = results[results['course_name'].str.lower() != course_name.lower()]

        return results.head(n)

    def recommend_by_interests(self, interests: str, n: int = 10,
                                difficulty: str = None) -> pd.DataFrame:
        """Recommend courses based on free-text interests.

        Args:
            interests: Natural language description of what the user wants to learn
            n: Number of recommendations
            difficulty: Optional difficulty filter

        Returns:
            DataFrame with recommended courses
        """
        return self.em.search_courses(
            interests, n_results=n, difficulty=difficulty
        )

    def recommend_by_skills(self, target_skills: List[str], n: int = 10,
                             difficulty: str = None) -> pd.DataFrame:
        """Recommend courses that teach specific skills.

        Args:
            target_skills: List of skills the user wants to learn
            n: Number of recommendations
            difficulty: Optional difficulty filter

        Returns:
            DataFrame with recommended courses ranked by skill match
        """
        if self.courses_df.empty:
            # Fall back to semantic search
            query = ", ".join(target_skills)
            return self.em.search_courses(query, n_results=n, difficulty=difficulty)

        target_set = set(s.lower() for s in target_skills)

        # Score each course by how many target skills it covers
        scores = []
        for _, row in self.courses_df.iterrows():
            course_skills = set(s.lower() for s in row.get('skills_list', []))
            overlap = target_set & course_skills
            if overlap:
                scores.append({
                    'course_name': row['course_name'],
                    'difficulty_level': row.get('difficulty_level', 'Mixed'),
                    'category': row.get('category', ''),
                    'rating': row.get('course_rating', 0),
                    'university': row.get('university', ''),
                    'skill_match_count': len(overlap),
                    'matched_skills': list(overlap),
                    'total_skills': len(course_skills),
                    'skill_match_ratio': len(overlap) / len(target_set) if target_set else 0
                })

        if not scores:
            # Fall back to semantic search
            query = ", ".join(target_skills)
            return self.em.search_courses(query, n_results=n, difficulty=difficulty)

        result_df = pd.DataFrame(scores)

        # Filter by difficulty if specified
        if difficulty:
            result_df = result_df[result_df['difficulty_level'] == difficulty]

        # Sort by skill match ratio, then rating
        result_df = result_df.sort_values(
            ['skill_match_ratio', 'rating'],
            ascending=[False, False]
        )

        return result_df.head(n)

    def recommend_learning_path(self, goal: str, current_skills: List[str] = None,
                                 n_per_level: int = 3) -> Dict[str, pd.DataFrame]:
        """Generate an ordered learning path from beginner to advanced.

        Args:
            goal: What the user wants to achieve (e.g., "become a data scientist")
            current_skills: Skills the user already has
            n_per_level: Number of courses per difficulty level

        Returns:
            Dict with keys 'Beginner', 'Intermediate', 'Advanced', each containing a DataFrame
        """
        current_skills = current_skills or []
        current_set = set(s.lower() for s in current_skills)

        path = {}
        for level in ['Beginner', 'Intermediate', 'Advanced']:
            results = self.em.search_courses(
                goal, n_results=n_per_level * 3, difficulty=level
            )

            if results.empty:
                path[level] = pd.DataFrame()
                continue

            # If user has current skills, deprioritize courses covering only known skills
            if current_set and not self.courses_df.empty:
                novelty_scores = []
                for _, row in results.iterrows():
                    # Find matching course in full data
                    match = self.courses_df[
                        self.courses_df['course_name'] == row['course_name']
                    ]
                    if not match.empty:
                        course_skills = set(
                            s.lower() for s in match.iloc[0].get('skills_list', [])
                        )
                        new_skills = course_skills - current_set
                        novelty_scores.append(len(new_skills))
                    else:
                        novelty_scores.append(0)

                results['novelty'] = novelty_scores
                results = results.sort_values(
                    ['novelty', 'similarity_score'], ascending=[False, False]
                )

            path[level] = results.head(n_per_level)

        return path

    def get_skill_gap(self, goal_skills: List[str],
                       current_skills: List[str]) -> Dict:
        """Analyze the gap between current and goal skills.

        Args:
            goal_skills: Skills needed for the goal
            current_skills: Skills the user already has

        Returns:
            Dict with gap analysis
        """
        goal_set = set(s.lower() for s in goal_skills)
        current_set = set(s.lower() for s in current_skills)

        missing = goal_set - current_set
        covered = goal_set & current_set

        # Find courses that teach missing skills
        recommendations = self.recommend_by_skills(list(missing), n=10)

        return {
            'goal_skills': list(goal_set),
            'current_skills': list(current_set),
            'missing_skills': list(missing),
            'covered_skills': list(covered),
            'completion_pct': len(covered) / len(goal_set) * 100 if goal_set else 100,
            'recommended_courses': recommendations
        }

    def get_popular_skills(self, category: str = None, top_n: int = 20) -> List[Dict]:
        """Get the most popular skills across all courses.

        Args:
            category: Optional category filter
            top_n: Number of top skills to return

        Returns:
            List of dicts with skill name and count
        """
        if self.courses_df.empty:
            return []

        df = self.courses_df
        if category:
            df = df[df['category'] == category]

        all_skills = []
        for skills in df['skills_list']:
            if isinstance(skills, list):
                all_skills.extend(s.lower() for s in skills)

        counter = Counter(all_skills)
        return [{'skill': skill, 'count': count} for skill, count in counter.most_common(top_n)]


def test_recommender():
    """Test the content-based recommender."""
    print("="*60)
    print("TESTING CONTENT-BASED RECOMMENDER")
    print("="*60)

    rec = ContentBasedRecommender()

    # Ensure embeddings are loaded
    if rec.em.collection.count() == 0:
        print("\nLoading embeddings...")
        if not rec.courses_df.empty:
            rec.em.add_courses(rec.courses_df)
        else:
            print("No course data available")
            return

    # Test 1: Similar courses
    print("\n" + "-"*60)
    print("TEST 1: Courses similar to 'Machine Learning'")
    print("-"*60)
    results = rec.recommend_similar("Machine Learning", n=5)
    if not results.empty:
        for _, r in results.iterrows():
            print(f"  {r['course_name']} ({r['difficulty_level']}) - score: {r['similarity_score']:.3f}")

    # Test 2: Interest-based
    print("\n" + "-"*60)
    print("TEST 2: Courses for 'I want to learn web development with React'")
    print("-"*60)
    results = rec.recommend_by_interests("I want to learn web development with React", n=5)
    if not results.empty:
        for _, r in results.iterrows():
            print(f"  {r['course_name']} ({r['difficulty_level']}) - score: {r['similarity_score']:.3f}")

    # Test 3: Skill-based
    print("\n" + "-"*60)
    print("TEST 3: Courses for skills: Python, SQL, Data Analysis")
    print("-"*60)
    results = rec.recommend_by_skills(['Python', 'SQL', 'Data Analysis'], n=5)
    if not results.empty:
        for _, r in results.iterrows():
            matched = r.get('matched_skills', [])
            print(f"  {r['course_name']} - matched: {matched}")

    # Test 4: Learning path
    print("\n" + "-"*60)
    print("TEST 4: Learning path for 'data science'")
    print("-"*60)
    path = rec.recommend_learning_path("data science", n_per_level=2)
    for level, courses in path.items():
        print(f"\n  {level}:")
        if not courses.empty:
            for _, r in courses.iterrows():
                print(f"    - {r['course_name']}")
        else:
            print("    (no courses found)")

    # Test 5: Popular skills
    print("\n" + "-"*60)
    print("TEST 5: Top 10 most popular skills")
    print("-"*60)
    skills = rec.get_popular_skills(top_n=10)
    for s in skills:
        print(f"  {s['skill']}: {s['count']} courses")

    print("\n" + "="*60)
    print("Content-based recommender test completed!")
    print("="*60)


if __name__ == "__main__":
    test_recommender()
