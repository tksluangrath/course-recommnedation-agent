"""
Hybrid Recommendation Engine

Combines content-based and collaborative filtering approaches:
1. Weighted hybrid - blend scores from both methods
2. Difficulty-aware re-ranking - order by learning progression
3. Diversity-aware selection - avoid recommending too-similar courses
"""

import sys
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))

from database import DatabaseManager
from embeddings import EmbeddingManager
from content_based import ContentBasedRecommender
from collaborative import CollaborativeRecommender


class HybridRecommender:
    """Hybrid recommendation engine combining content-based and collaborative filtering."""

    DIFFICULTY_ORDER = {'Beginner': 0, 'Intermediate': 1, 'Advanced': 2, 'Mixed': 1}

    def __init__(self, content_weight: float = 0.6, collab_weight: float = 0.4):
        """Initialize hybrid recommender.

        Args:
            content_weight: Weight for content-based scores (0-1)
            collab_weight: Weight for collaborative filtering scores (0-1)
        """
        self.content_weight = content_weight
        self.collab_weight = collab_weight

        self.db = DatabaseManager()
        self.em = EmbeddingManager()
        self.content_rec = ContentBasedRecommender(self.db, self.em)
        self.collab_rec = CollaborativeRecommender(self.db)

        # Generate synthetic interactions for collaborative filtering
        self.interactions = self.collab_rec.generate_synthetic_users(n_users=100)

    def recommend(self, query: str, user_history: Dict[str, float] = None,
                   n: int = 10, difficulty: str = None) -> pd.DataFrame:
        """Generate hybrid recommendations.

        Args:
            query: What the user wants to learn
            user_history: Optional dict of {course_name: rating} for personalization
            n: Number of recommendations
            difficulty: Optional difficulty filter

        Returns:
            DataFrame with ranked recommendations
        """
        # Get content-based recommendations
        content_results = self.content_rec.recommend_by_interests(
            query, n=n * 2, difficulty=difficulty
        )

        # Normalize content scores
        if not content_results.empty and 'similarity_score' in content_results.columns:
            max_score = content_results['similarity_score'].max()
            if max_score > 0:
                content_results['content_score'] = content_results['similarity_score'] / max_score
            else:
                content_results['content_score'] = 0
        else:
            return content_results.head(n)

        # Get collaborative recommendations if user has history
        if user_history and len(user_history) > 0:
            collab_results = self.collab_rec.recommend_user_user(
                user_history, self.interactions, n=n * 2
            )

            if not collab_results.empty and 'predicted_rating' in collab_results.columns:
                max_rating = collab_results['predicted_rating'].max()
                if max_rating > 0:
                    collab_results['collab_score'] = collab_results['predicted_rating'] / max_rating
                else:
                    collab_results['collab_score'] = 0

                # Merge scores
                merged = content_results.merge(
                    collab_results[['course_name', 'collab_score']],
                    on='course_name',
                    how='left'
                )
                merged['collab_score'] = merged['collab_score'].fillna(0)
            else:
                merged = content_results.copy()
                merged['collab_score'] = 0
        else:
            merged = content_results.copy()
            merged['collab_score'] = 0

        # Compute hybrid score
        merged['hybrid_score'] = (
            self.content_weight * merged['content_score'] +
            self.collab_weight * merged['collab_score']
        )

        # Sort by hybrid score
        merged = merged.sort_values('hybrid_score', ascending=False)

        # Apply diversity: avoid too many courses from the same category
        merged = self._diversify(merged, n)

        return merged.head(n)

    def recommend_learning_path(self, goal: str,
                                 current_skills: List[str] = None,
                                 user_history: Dict[str, float] = None,
                                 n_per_level: int = 3) -> Dict[str, pd.DataFrame]:
        """Generate a personalized learning path.

        Combines content-based path generation with collaborative filtering
        to create a personalized learning journey.

        Args:
            goal: Learning goal
            current_skills: Skills the user already has
            user_history: Past course ratings
            n_per_level: Courses per difficulty level

        Returns:
            Dict with Beginner/Intermediate/Advanced DataFrames
        """
        # Get content-based learning path
        path = self.content_rec.recommend_learning_path(
            goal, current_skills, n_per_level=n_per_level * 2
        )

        # Re-rank with collaborative scores if user has history
        if user_history:
            collab_results = self.collab_rec.recommend_user_user(
                user_history, self.interactions, n=50
            )

            if not collab_results.empty:
                collab_scores = dict(zip(
                    collab_results['course_name'],
                    collab_results['predicted_rating']
                ))

                for level in path:
                    if not path[level].empty:
                        path[level]['collab_boost'] = path[level]['course_name'].map(
                            collab_scores
                        ).fillna(0)

                        # Re-sort with boost
                        if 'similarity_score' in path[level].columns:
                            path[level]['combined'] = (
                                path[level]['similarity_score'] +
                                0.3 * path[level]['collab_boost']
                            )
                            path[level] = path[level].sort_values(
                                'combined', ascending=False
                            )

        # Trim to requested size
        for level in path:
            path[level] = path[level].head(n_per_level)

        return path

    def _diversify(self, df: pd.DataFrame, n: int,
                    max_per_category: int = 3) -> pd.DataFrame:
        """Ensure diversity in recommendations.

        Limits courses from any single category to avoid monotony.

        Args:
            df: Ranked recommendations
            n: Total recommendations needed
            max_per_category: Max courses from same category

        Returns:
            Diversified DataFrame
        """
        if 'category' not in df.columns:
            return df.head(n)

        selected = []
        category_counts = {}

        for _, row in df.iterrows():
            cat = row.get('category', 'Other')
            count = category_counts.get(cat, 0)

            if count < max_per_category:
                selected.append(row)
                category_counts[cat] = count + 1

            if len(selected) >= n:
                break

        return pd.DataFrame(selected)


def test_hybrid():
    """Test the hybrid recommender."""
    print("="*60)
    print("TESTING HYBRID RECOMMENDER")
    print("="*60)

    rec = HybridRecommender()

    # Ensure embeddings exist
    if rec.em.collection.count() == 0:
        print("\nLoading embeddings...")
        rec.em.add_courses(rec.content_rec.courses_df)

    # Test 1: No user history (cold start - content-based only)
    print("\n" + "-"*60)
    print("TEST 1: Cold start - 'machine learning' (no user history)")
    print("-"*60)
    results = rec.recommend("machine learning", n=5)
    if not results.empty:
        for _, r in results.iterrows():
            print(f"  {r['course_name']} ({r.get('difficulty_level', '')}) "
                  f"- hybrid: {r['hybrid_score']:.3f}")

    # Test 2: With user history (personalized)
    print("\n" + "-"*60)
    print("TEST 2: Personalized - user who liked data science courses")
    print("-"*60)
    ds_courses = rec.content_rec.courses_df[
        rec.content_rec.courses_df['category'] == 'Data Science'
    ]['course_name'].head(3).tolist()

    if ds_courses:
        user_prefs = {c: 4.5 for c in ds_courses}
        results = rec.recommend("advanced analytics", user_history=user_prefs, n=5)
        if not results.empty:
            for _, r in results.iterrows():
                print(f"  {r['course_name']} - hybrid: {r['hybrid_score']:.3f} "
                      f"(content: {r['content_score']:.2f}, collab: {r['collab_score']:.2f})")

    # Test 3: Learning path
    print("\n" + "-"*60)
    print("TEST 3: Learning path for 'become a data scientist'")
    print("-"*60)
    path = rec.recommend_learning_path(
        "become a data scientist",
        current_skills=["Python", "Statistics"],
        n_per_level=2
    )
    for level, courses in path.items():
        print(f"\n  {level}:")
        if not courses.empty:
            for _, r in courses.iterrows():
                print(f"    - {r['course_name']}")

    print("\n" + "="*60)
    print("Hybrid recommender test completed!")
    print("="*60)


if __name__ == "__main__":
    test_hybrid()
