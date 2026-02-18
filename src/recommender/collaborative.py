"""
Collaborative Filtering Recommendation Engine

Implements:
1. Item-item collaborative filtering (course similarity based on shared skills/ratings)
2. User-user collaborative filtering (simulated users with synthetic interaction data)
3. Cold-start handling
"""

import sys
import ast
import random
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))

from database import DatabaseManager


class CollaborativeRecommender:
    """Collaborative filtering recommendation engine."""

    def __init__(self, db: DatabaseManager = None):
        """Initialize with database manager."""
        self.db = db or DatabaseManager()

        csv_path = Path("data/processed/cleaned_courses.csv")
        if csv_path.exists():
            self.courses_df = pd.read_csv(csv_path)
            if 'extracted_skills' in self.courses_df.columns:
                self.courses_df['skills_list'] = self.courses_df['extracted_skills'].apply(
                    self._parse_skills
                )
        else:
            self.courses_df = pd.DataFrame()

        # Precompute item-item similarity
        self.item_similarity = None
        self.skill_matrix = None
        self.course_names = None

    @staticmethod
    def _parse_skills(skills_raw) -> List[str]:
        if pd.isna(skills_raw):
            return []
        if isinstance(skills_raw, list):
            return skills_raw
        try:
            return ast.literal_eval(str(skills_raw))
        except (ValueError, SyntaxError):
            return [s.strip() for s in str(skills_raw).split(',') if s.strip()]

    def build_skill_matrix(self):
        """Build a course-skill matrix for item-item similarity.

        Each row is a course, each column is a skill.
        Value is 1 if the course teaches that skill, 0 otherwise.
        """
        if self.courses_df.empty:
            return

        print("Building course-skill matrix...")

        # Collect all unique skills
        all_skills = set()
        for skills in self.courses_df['skills_list']:
            if isinstance(skills, list):
                all_skills.update(s.lower() for s in skills)

        all_skills = sorted(all_skills)
        skill_to_idx = {skill: i for i, skill in enumerate(all_skills)}

        n_courses = len(self.courses_df)
        n_skills = len(all_skills)

        # Build sparse matrix
        rows, cols, data = [], [], []
        for i, skills in enumerate(self.courses_df['skills_list']):
            if isinstance(skills, list):
                for skill in skills:
                    skill_lower = skill.lower()
                    if skill_lower in skill_to_idx:
                        rows.append(i)
                        cols.append(skill_to_idx[skill_lower])
                        data.append(1.0)

        self.skill_matrix = csr_matrix((data, (rows, cols)), shape=(n_courses, n_skills))
        self.course_names = self.courses_df['course_name'].tolist()

        print(f"Matrix shape: {n_courses} courses x {n_skills} skills")

    def compute_item_similarity(self):
        """Compute item-item similarity based on shared skills."""
        if self.skill_matrix is None:
            self.build_skill_matrix()

        if self.skill_matrix is None:
            return

        print("Computing item-item similarity...")
        self.item_similarity = cosine_similarity(self.skill_matrix)
        print(f"Similarity matrix shape: {self.item_similarity.shape}")

    def recommend_item_item(self, course_name: str, n: int = 10) -> pd.DataFrame:
        """Recommend courses similar to a given course using item-item CF.

        Based on shared skills between courses.

        Args:
            course_name: Name of the course
            n: Number of recommendations

        Returns:
            DataFrame with recommended courses
        """
        if self.item_similarity is None:
            self.compute_item_similarity()

        if self.item_similarity is None or self.courses_df.empty:
            return pd.DataFrame()

        # Find course index
        matches = self.courses_df[
            self.courses_df['course_name'].str.lower().str.contains(course_name.lower())
        ]

        if matches.empty:
            return pd.DataFrame()

        course_idx = matches.index[0]
        similarities = self.item_similarity[course_idx]

        # Get top N similar courses (excluding itself)
        similar_indices = np.argsort(similarities)[::-1][1:n+1]

        results = []
        for idx in similar_indices:
            if similarities[idx] > 0:
                row = self.courses_df.iloc[idx]
                results.append({
                    'course_name': row['course_name'],
                    'difficulty_level': row.get('difficulty_level', 'Mixed'),
                    'category': row.get('category', ''),
                    'rating': row.get('course_rating', 0),
                    'university': row.get('university', ''),
                    'skill_similarity': similarities[idx]
                })

        return pd.DataFrame(results)

    def generate_synthetic_users(self, n_users: int = 100, seed: int = 42) -> pd.DataFrame:
        """Generate synthetic user interaction data for testing.

        Simulates users who tend to enroll in related courses
        (same category, progressive difficulty).

        Args:
            n_users: Number of synthetic users
            seed: Random seed for reproducibility

        Returns:
            DataFrame with user-course interactions
        """
        random.seed(seed)
        np.random.seed(seed)

        if self.courses_df.empty:
            return pd.DataFrame()

        print(f"Generating {n_users} synthetic users...")

        interactions = []
        categories = self.courses_df['category'].unique()

        for user_id in range(n_users):
            # Each user has 1-2 preferred categories
            n_prefs = random.randint(1, 2)
            preferred_cats = random.sample(list(categories), min(n_prefs, len(categories)))

            # User enrolls in 3-10 courses
            n_courses = random.randint(3, 10)

            # Prefer courses from preferred categories
            cat_courses = self.courses_df[
                self.courses_df['category'].isin(preferred_cats)
            ]

            if len(cat_courses) < n_courses:
                # Add some random courses too
                other_courses = self.courses_df[
                    ~self.courses_df['category'].isin(preferred_cats)
                ].sample(min(n_courses - len(cat_courses), len(self.courses_df)))
                selected = pd.concat([cat_courses, other_courses])
            else:
                selected = cat_courses.sample(n_courses)

            for _, course in selected.iterrows():
                # Generate a rating (biased toward higher for preferred categories)
                if course['category'] in preferred_cats:
                    rating = np.clip(np.random.normal(4.2, 0.5), 1, 5)
                else:
                    rating = np.clip(np.random.normal(3.5, 0.8), 1, 5)

                interactions.append({
                    'user_id': f'user_{user_id}',
                    'course_name': course['course_name'],
                    'course_idx': course.name,
                    'category': course['category'],
                    'rating': round(rating, 1),
                    'interaction_type': random.choice(['enrolled', 'completed', 'completed'])
                })

        interactions_df = pd.DataFrame(interactions)
        print(f"Generated {len(interactions_df)} interactions for {n_users} users")

        return interactions_df

    def build_user_item_matrix(self, interactions_df: pd.DataFrame) -> np.ndarray:
        """Build user-item rating matrix from interactions.

        Args:
            interactions_df: DataFrame with user-course interactions

        Returns:
            User-item rating matrix
        """
        # Create pivot table
        pivot = interactions_df.pivot_table(
            index='user_id',
            columns='course_name',
            values='rating',
            aggfunc='mean'
        ).fillna(0)

        self._user_ids = pivot.index.tolist()
        self._course_names_cf = pivot.columns.tolist()

        return pivot.values

    def recommend_user_user(self, user_interactions: Dict[str, float],
                             interactions_df: pd.DataFrame,
                             n: int = 10) -> pd.DataFrame:
        """Recommend courses using user-user collaborative filtering.

        Finds similar users and recommends what they liked.

        Args:
            user_interactions: Dict of {course_name: rating} for the current user
            interactions_df: All user interactions
            n: Number of recommendations

        Returns:
            DataFrame with recommended courses
        """
        # Build user-item matrix
        matrix = self.build_user_item_matrix(interactions_df)

        # Create vector for current user
        user_vector = np.zeros(len(self._course_names_cf))
        for course, rating in user_interactions.items():
            if course in self._course_names_cf:
                idx = self._course_names_cf.index(course)
                user_vector[idx] = rating

        if user_vector.sum() == 0:
            return pd.DataFrame()

        # Compute similarity between current user and all users
        user_sims = cosine_similarity([user_vector], matrix)[0]

        # Weighted average of similar users' ratings
        # Only consider top 20 most similar users
        top_user_indices = np.argsort(user_sims)[::-1][:20]

        predicted_ratings = np.zeros(len(self._course_names_cf))
        sim_sum = np.zeros(len(self._course_names_cf))

        for uid in top_user_indices:
            sim = user_sims[uid]
            if sim > 0:
                for cid in range(len(self._course_names_cf)):
                    if matrix[uid, cid] > 0:
                        predicted_ratings[cid] += sim * matrix[uid, cid]
                        sim_sum[cid] += sim

        # Normalize
        mask = sim_sum > 0
        predicted_ratings[mask] /= sim_sum[mask]

        # Remove courses the user already interacted with
        for course in user_interactions:
            if course in self._course_names_cf:
                idx = self._course_names_cf.index(course)
                predicted_ratings[idx] = 0

        # Get top N
        top_indices = np.argsort(predicted_ratings)[::-1][:n]

        results = []
        for idx in top_indices:
            if predicted_ratings[idx] > 0:
                course_name = self._course_names_cf[idx]
                # Find course details
                match = self.courses_df[
                    self.courses_df['course_name'] == course_name
                ]
                if not match.empty:
                    row = match.iloc[0]
                    results.append({
                        'course_name': course_name,
                        'predicted_rating': round(predicted_ratings[idx], 2),
                        'difficulty_level': row.get('difficulty_level', 'Mixed'),
                        'category': row.get('category', ''),
                        'rating': row.get('course_rating', 0),
                        'university': row.get('university', '')
                    })

        return pd.DataFrame(results)


def test_collaborative():
    """Test collaborative filtering recommender."""
    print("="*60)
    print("TESTING COLLABORATIVE FILTERING RECOMMENDER")
    print("="*60)

    rec = CollaborativeRecommender()

    if rec.courses_df.empty:
        print("No course data available")
        return

    # Test 1: Item-item similarity
    print("\n" + "-"*60)
    print("TEST 1: Item-item similarity (courses similar by skills)")
    print("-"*60)
    results = rec.recommend_item_item("Machine Learning", n=5)
    if not results.empty:
        for _, r in results.iterrows():
            print(f"  {r['course_name']} - similarity: {r['skill_similarity']:.3f}")
    else:
        print("  No results")

    # Test 2: Generate synthetic users
    print("\n" + "-"*60)
    print("TEST 2: Generating synthetic user data")
    print("-"*60)
    interactions = rec.generate_synthetic_users(n_users=50)
    print(f"  Users: {interactions['user_id'].nunique()}")
    print(f"  Interactions: {len(interactions)}")
    print(f"  Avg courses per user: {len(interactions) / interactions['user_id'].nunique():.1f}")

    # Test 3: User-user collaborative filtering
    print("\n" + "-"*60)
    print("TEST 3: User-user recommendations")
    print("-"*60)
    # Simulate a user who likes data science courses
    sample_courses = rec.courses_df[
        rec.courses_df['category'] == 'Data Science'
    ]['course_name'].head(3).tolist()

    if sample_courses:
        user_prefs = {course: 4.5 for course in sample_courses}
        print(f"  User liked: {sample_courses}")

        results = rec.recommend_user_user(user_prefs, interactions, n=5)
        if not results.empty:
            print("\n  Recommendations:")
            for _, r in results.iterrows():
                print(f"    {r['course_name']} (predicted: {r['predicted_rating']}) - {r['category']}")
        else:
            print("  No recommendations (cold start)")

    print("\n" + "="*60)
    print("Collaborative filtering test completed!")
    print("="*60)


if __name__ == "__main__":
    test_collaborative()
