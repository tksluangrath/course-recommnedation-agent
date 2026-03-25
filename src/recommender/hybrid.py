"""
Hybrid Recommendation Engine

Combines content-based and collaborative filtering:
- CollaborativeRecommender: item-item and user-user similarity via synthetic interactions
- HybridRecommender: 60/40 weighted blend with diversity controls
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
from embeddings import EmbeddingManager
from content_based import ContentBasedRecommender


# ---------------------------------------------------------------------------
# Collaborative filtering
# ---------------------------------------------------------------------------

class CollaborativeRecommender:
    """Item-item and user-user collaborative filtering using synthetic interactions."""

    def __init__(self, db: DatabaseManager = None):
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
        """Build a sparse course × skill matrix for item-item similarity."""
        if self.courses_df.empty:
            return

        all_skills = sorted({
            s.lower()
            for skills in self.courses_df['skills_list']
            if isinstance(skills, list)
            for s in skills
        })
        skill_to_idx = {s: i for i, s in enumerate(all_skills)}

        rows, cols, data = [], [], []
        for i, skills in enumerate(self.courses_df['skills_list']):
            if isinstance(skills, list):
                for skill in skills:
                    sl = skill.lower()
                    if sl in skill_to_idx:
                        rows.append(i)
                        cols.append(skill_to_idx[sl])
                        data.append(1.0)

        n_courses, n_skills = len(self.courses_df), len(all_skills)
        self.skill_matrix = csr_matrix((data, (rows, cols)), shape=(n_courses, n_skills))
        self.course_names = self.courses_df['course_name'].tolist()

    def compute_item_similarity(self):
        """Compute cosine similarity between all courses based on shared skills."""
        if self.skill_matrix is None:
            self.build_skill_matrix()
        if self.skill_matrix is not None:
            self.item_similarity = cosine_similarity(self.skill_matrix)

    def recommend_item_item(self, course_name: str, n: int = 10) -> pd.DataFrame:
        """Find courses most similar to a given course by shared skills."""
        if self.item_similarity is None:
            self.compute_item_similarity()
        if self.item_similarity is None or self.courses_df.empty:
            return pd.DataFrame()

        matches = self.courses_df[
            self.courses_df['course_name'].str.lower().str.contains(course_name.lower())
        ]
        if matches.empty:
            return pd.DataFrame()

        course_idx = matches.index[0]
        sims = self.item_similarity[course_idx]
        top_idxs = np.argsort(sims)[::-1][1:n + 1]

        results = []
        for idx in top_idxs:
            if sims[idx] > 0:
                row = self.courses_df.iloc[idx]
                results.append({
                    'course_name': row['course_name'],
                    'difficulty_level': row.get('difficulty_level', 'Mixed'),
                    'category': row.get('category', ''),
                    'rating': row.get('course_rating', 0),
                    'university': row.get('university', ''),
                    'skill_similarity': sims[idx],
                })
        return pd.DataFrame(results)

    def generate_synthetic_users(self, n_users: int = 100, seed: int = 42) -> pd.DataFrame:
        """Create synthetic user-course interaction data for collaborative filtering."""
        random.seed(seed)
        np.random.seed(seed)

        if self.courses_df.empty:
            return pd.DataFrame()

        interactions = []
        categories = self.courses_df['category'].unique()

        for user_id in range(n_users):
            preferred_cats = random.sample(list(categories), min(random.randint(1, 2), len(categories)))
            n_courses = random.randint(3, 10)

            cat_courses = self.courses_df[self.courses_df['category'].isin(preferred_cats)]
            if len(cat_courses) < n_courses:
                other = self.courses_df[~self.courses_df['category'].isin(preferred_cats)]
                selected = pd.concat([cat_courses, other.sample(min(n_courses - len(cat_courses), len(other)))])
            else:
                selected = cat_courses.sample(n_courses)

            for _, course in selected.iterrows():
                mu = 4.2 if course['category'] in preferred_cats else 3.5
                rating = np.clip(np.random.normal(mu, 0.5 if mu == 4.2 else 0.8), 1, 5)
                interactions.append({
                    'user_id': f'user_{user_id}',
                    'course_name': course['course_name'],
                    'course_idx': course.name,
                    'category': course['category'],
                    'rating': round(rating, 1),
                    'interaction_type': random.choice(['enrolled', 'completed', 'completed']),
                })

        return pd.DataFrame(interactions)

    def build_user_item_matrix(self, interactions_df: pd.DataFrame) -> np.ndarray:
        """Pivot interactions into a user × course rating matrix."""
        pivot = interactions_df.pivot_table(
            index='user_id', columns='course_name', values='rating', aggfunc='mean'
        ).fillna(0)
        self._user_ids = pivot.index.tolist()
        self._course_names_cf = pivot.columns.tolist()
        return pivot.values

    def recommend_user_user(self, user_interactions: Dict[str, float],
                             interactions_df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
        """Recommend courses based on ratings from the most similar users."""
        matrix = self.build_user_item_matrix(interactions_df)

        user_vector = np.zeros(len(self._course_names_cf))
        for course, rating in user_interactions.items():
            if course in self._course_names_cf:
                user_vector[self._course_names_cf.index(course)] = rating

        if user_vector.sum() == 0:
            return pd.DataFrame()

        user_sims = cosine_similarity([user_vector], matrix)[0]
        top_users = np.argsort(user_sims)[::-1][:20]

        predicted = np.zeros(len(self._course_names_cf))
        sim_sum = np.zeros(len(self._course_names_cf))
        for uid in top_users:
            sim = user_sims[uid]
            if sim > 0:
                for cid in range(len(self._course_names_cf)):
                    if matrix[uid, cid] > 0:
                        predicted[cid] += sim * matrix[uid, cid]
                        sim_sum[cid] += sim

        mask = sim_sum > 0
        predicted[mask] /= sim_sum[mask]

        for course in user_interactions:
            if course in self._course_names_cf:
                predicted[self._course_names_cf.index(course)] = 0

        top_idxs = np.argsort(predicted)[::-1][:n]
        results = []
        for idx in top_idxs:
            if predicted[idx] > 0:
                name = self._course_names_cf[idx]
                match = self.courses_df[self.courses_df['course_name'] == name]
                if not match.empty:
                    row = match.iloc[0]
                    results.append({
                        'course_name': name,
                        'predicted_rating': round(predicted[idx], 2),
                        'difficulty_level': row.get('difficulty_level', 'Mixed'),
                        'category': row.get('category', ''),
                        'rating': row.get('course_rating', 0),
                        'university': row.get('university', ''),
                    })
        return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Hybrid recommender
# ---------------------------------------------------------------------------

class HybridRecommender:
    """60/40 blend of content-based and collaborative filtering with diversity controls."""

    DIFFICULTY_ORDER = {'Beginner': 0, 'Intermediate': 1, 'Advanced': 2, 'Mixed': 1}

    def __init__(self, content_weight: float = 0.6, collab_weight: float = 0.4):
        self.content_weight = content_weight
        self.collab_weight = collab_weight

        self.db = DatabaseManager()
        self.em = EmbeddingManager()
        self.content_rec = ContentBasedRecommender(self.db, self.em)
        self.collab_rec = CollaborativeRecommender(self.db)
        self.interactions = self.collab_rec.generate_synthetic_users(n_users=100)

    def recommend(self, query: str, user_history: Dict[str, float] = None,
                   n: int = 10, difficulty: str = None) -> pd.DataFrame:
        """Hybrid recommendations blending content and collaborative scores."""
        content_results = self.content_rec.recommend_by_interests(query, n=n * 2, difficulty=difficulty)

        if content_results.empty or 'similarity_score' not in content_results.columns:
            return content_results.head(n)

        max_score = content_results['similarity_score'].max()
        content_results['content_score'] = (
            content_results['similarity_score'] / max_score if max_score > 0 else 0
        )

        merged = content_results.copy()
        merged['collab_score'] = 0.0

        if user_history:
            collab_results = self.collab_rec.recommend_user_user(
                user_history, self.interactions, n=n * 2
            )
            if not collab_results.empty and 'predicted_rating' in collab_results.columns:
                max_r = collab_results['predicted_rating'].max()
                if max_r > 0:
                    collab_results['collab_score'] = collab_results['predicted_rating'] / max_r
                    merged = merged.merge(
                        collab_results[['course_name', 'collab_score']],
                        on='course_name', how='left'
                    )
                    merged['collab_score'] = merged['collab_score'].fillna(0)

        merged['hybrid_score'] = (
            self.content_weight * merged['content_score'] +
            self.collab_weight * merged['collab_score']
        )
        merged = merged.sort_values('hybrid_score', ascending=False)
        return self._diversify(merged, n)

    def recommend_learning_path(self, goal: str, current_skills: List[str] = None,
                                 user_history: Dict[str, float] = None,
                                 n_per_level: int = 3) -> Dict[str, pd.DataFrame]:
        """Personalized learning path with optional collaborative re-ranking."""
        path = self.content_rec.recommend_learning_path(goal, current_skills, n_per_level=n_per_level * 2)

        if user_history:
            collab_results = self.collab_rec.recommend_user_user(
                user_history, self.interactions, n=50
            )
            if not collab_results.empty:
                collab_scores = dict(zip(collab_results['course_name'], collab_results['predicted_rating']))
                for level in path:
                    if path[level].empty:
                        continue
                    hours_backup = None
                    if 'estimated_hours' in path[level].columns:
                        hours_backup = path[level][['course_name', 'estimated_hours']].copy()

                    path[level]['collab_boost'] = path[level]['course_name'].map(collab_scores).fillna(0)
                    if 'similarity_score' in path[level].columns:
                        path[level]['combined'] = (
                            path[level]['similarity_score'] + 0.3 * path[level]['collab_boost']
                        )
                        path[level] = path[level].sort_values('combined', ascending=False)

                    if hours_backup is not None and 'estimated_hours' not in path[level].columns:
                        path[level] = path[level].merge(hours_backup, on='course_name', how='left')

        for level in path:
            path[level] = path[level].head(n_per_level)
        return path

    def _diversify(self, df: pd.DataFrame, n: int, max_per_category: int = 3) -> pd.DataFrame:
        """Cap courses per category to avoid monotonous recommendations."""
        if 'category' not in df.columns:
            return df.head(n)

        selected, counts = [], {}
        for _, row in df.iterrows():
            cat = row.get('category', 'Other')
            if counts.get(cat, 0) < max_per_category:
                selected.append(row)
                counts[cat] = counts.get(cat, 0) + 1
            if len(selected) >= n:
                break
        return pd.DataFrame(selected)
