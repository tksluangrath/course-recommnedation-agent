"""
Recommendation Evaluation Metrics

Evaluates recommendation quality using:
1. Precision@K - fraction of recommended items that are relevant
2. Recall@K - fraction of relevant items that are recommended
3. NDCG@K - accounts for ranking position of relevant items
4. Coverage - fraction of catalog recommended across all users
5. Diversity - how different recommendations are from each other
"""

import sys
import numpy as np
import pandas as pd
from typing import List, Dict
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
sys.path.insert(0, str(Path(__file__).parent))

from database import DatabaseManager
from hybrid import CollaborativeRecommender
from content_based import ContentBasedRecommender


def precision_at_k(recommended: List[str], relevant: List[str], k: int) -> float:
    """Precision@K: fraction of top-K recommendations that are relevant.

    Args:
        recommended: Ordered list of recommended course names
        relevant: List of relevant (ground truth) course names
        k: Number of recommendations to consider
    """
    rec_at_k = recommended[:k]
    relevant_set = set(relevant)
    hits = sum(1 for r in rec_at_k if r in relevant_set)
    return hits / k if k > 0 else 0.0


def recall_at_k(recommended: List[str], relevant: List[str], k: int) -> float:
    """Recall@K: fraction of relevant items found in top-K recommendations.

    Args:
        recommended: Ordered list of recommended course names
        relevant: List of relevant (ground truth) course names
        k: Number of recommendations to consider
    """
    rec_at_k = set(recommended[:k])
    relevant_set = set(relevant)
    if not relevant_set:
        return 0.0
    hits = len(rec_at_k & relevant_set)
    return hits / len(relevant_set)


def ndcg_at_k(recommended: List[str], relevant: List[str], k: int) -> float:
    """Normalized Discounted Cumulative Gain at K.

    Higher positions contribute more to the score.

    Args:
        recommended: Ordered list of recommended course names
        relevant: List of relevant course names
        k: Number of recommendations to consider
    """
    relevant_set = set(relevant)

    # DCG
    dcg = 0.0
    for i, item in enumerate(recommended[:k]):
        if item in relevant_set:
            dcg += 1.0 / np.log2(i + 2)  # i+2 because log2(1) = 0

    # Ideal DCG
    ideal_hits = min(len(relevant_set), k)
    idcg = sum(1.0 / np.log2(i + 2) for i in range(ideal_hits))

    return dcg / idcg if idcg > 0 else 0.0


def catalog_coverage(all_recommendations: List[List[str]], catalog_size: int) -> float:
    """Fraction of the catalog that appears in any recommendation.

    Args:
        all_recommendations: List of recommendation lists (one per user)
        catalog_size: Total number of items in catalog
    """
    recommended_items = set()
    for recs in all_recommendations:
        recommended_items.update(recs)
    return len(recommended_items) / catalog_size if catalog_size > 0 else 0.0


def diversity(recommendations: List[str], courses_df: pd.DataFrame) -> float:
    """Intra-list diversity: how different the recommended courses are.

    Measured by category diversity (1 - fraction of most common category).

    Args:
        recommendations: List of course names
        courses_df: DataFrame with course data including 'category'
    """
    if not recommendations:
        return 0.0

    categories = []
    for course_name in recommendations:
        match = courses_df[courses_df['course_name'] == course_name]
        if not match.empty:
            categories.append(match.iloc[0].get('category', 'Other'))

    if not categories:
        return 0.0

    counter = Counter(categories)
    most_common_frac = counter.most_common(1)[0][1] / len(categories)
    return 1.0 - most_common_frac


class RecommenderEvaluator:
    """Evaluates recommendation systems."""

    def __init__(self):
        self.db = DatabaseManager()
        self.collab_rec = CollaborativeRecommender(self.db)

        csv_path = Path("data/processed/cleaned_courses.csv")
        if csv_path.exists():
            self.courses_df = pd.read_csv(csv_path)
        else:
            self.courses_df = pd.DataFrame()

    def evaluate_content_based(self, k: int = 10, n_tests: int = 20) -> Dict:
        """Evaluate content-based recommender using leave-one-out.

        For each test: pick a course, find its category mates as "relevant",
        then check if recommendations include courses from the same category.

        Args:
            k: Number of recommendations
            n_tests: Number of test cases

        Returns:
            Dict with evaluation metrics
        """
        print("\nEvaluating content-based recommender...")

        content_rec = ContentBasedRecommender(self.db)

        # Ensure embeddings exist
        if content_rec.em.collection.count() == 0:
            content_rec.em.add_courses(self.courses_df)

        if self.courses_df.empty:
            return {}

        # Sample test courses
        test_courses = self.courses_df.sample(min(n_tests, len(self.courses_df)))

        precisions, recalls, ndcgs, diversities = [], [], [], []
        all_recs = []

        for _, test_course in test_courses.iterrows():
            course_name = test_course['course_name']
            category = test_course.get('category', '')

            # "Relevant" = other courses in the same category
            relevant = self.courses_df[
                (self.courses_df['category'] == category) &
                (self.courses_df['course_name'] != course_name)
            ]['course_name'].tolist()

            if not relevant:
                continue

            # Get recommendations
            results = content_rec.recommend_similar(course_name, n=k)
            if results.empty:
                continue

            recommended = results['course_name'].tolist()
            all_recs.append(recommended)

            precisions.append(precision_at_k(recommended, relevant, k))
            recalls.append(recall_at_k(recommended, relevant, k))
            ndcgs.append(ndcg_at_k(recommended, relevant, k))
            diversities.append(diversity(recommended, self.courses_df))

        coverage = catalog_coverage(all_recs, len(self.courses_df))

        return {
            'precision@k': np.mean(precisions) if precisions else 0,
            'recall@k': np.mean(recalls) if recalls else 0,
            'ndcg@k': np.mean(ndcgs) if ndcgs else 0,
            'coverage': coverage,
            'diversity': np.mean(diversities) if diversities else 0,
            'n_tests': len(precisions),
            'k': k
        }

    def evaluate_collaborative(self, k: int = 10, n_tests: int = 20) -> Dict:
        """Evaluate collaborative filtering using synthetic users.

        Hold out one course per user, then check if it's recommended.

        Args:
            k: Number of recommendations
            n_tests: Number of test cases

        Returns:
            Dict with evaluation metrics
        """
        print("\nEvaluating collaborative filtering...")

        if self.courses_df.empty:
            return {}

        # Generate interactions
        interactions = self.collab_rec.generate_synthetic_users(n_users=100)

        # Group by user
        user_groups = interactions.groupby('user_id')

        precisions, recalls, ndcgs = [], [], []
        all_recs = []
        tests_done = 0

        for user_id, group in user_groups:
            if tests_done >= n_tests:
                break

            if len(group) < 3:
                continue

            # Hold out the last course as test
            sorted_group = group.sort_values('rating', ascending=False)
            test_course = sorted_group.iloc[0]['course_name']
            train_courses = sorted_group.iloc[1:]

            # Build user preferences from training data
            user_prefs = dict(zip(train_courses['course_name'], train_courses['rating']))

            # Get recommendations
            results = self.collab_rec.recommend_user_user(
                user_prefs, interactions, n=k
            )

            if results.empty:
                continue

            recommended = results['course_name'].tolist()
            relevant = [test_course]
            all_recs.append(recommended)

            precisions.append(precision_at_k(recommended, relevant, k))
            recalls.append(recall_at_k(recommended, relevant, k))
            ndcgs.append(ndcg_at_k(recommended, relevant, k))
            tests_done += 1

        coverage = catalog_coverage(all_recs, len(self.courses_df))

        return {
            'precision@k': np.mean(precisions) if precisions else 0,
            'recall@k': np.mean(recalls) if recalls else 0,
            'ndcg@k': np.mean(ndcgs) if ndcgs else 0,
            'coverage': coverage,
            'n_tests': len(precisions),
            'k': k
        }

    def run_full_evaluation(self, k: int = 10) -> Dict:
        """Run evaluation for all recommendation approaches.

        Args:
            k: Number of recommendations to evaluate

        Returns:
            Dict with metrics for each approach
        """
        print("="*60)
        print(f"FULL RECOMMENDATION EVALUATION (K={k})")
        print("="*60)

        results = {}

        # Content-based
        content_metrics = self.evaluate_content_based(k=k)
        results['content_based'] = content_metrics

        print("\nContent-Based Results:")
        for metric, value in content_metrics.items():
            print(f"  {metric}: {value:.4f}" if isinstance(value, float) else f"  {metric}: {value}")

        # Collaborative
        collab_metrics = self.evaluate_collaborative(k=k)
        results['collaborative'] = collab_metrics

        print("\nCollaborative Filtering Results:")
        for metric, value in collab_metrics.items():
            print(f"  {metric}: {value:.4f}" if isinstance(value, float) else f"  {metric}: {value}")

        # Summary
        print("\n" + "="*60)
        print("COMPARISON SUMMARY")
        print("="*60)
        print(f"{'Metric':<20} {'Content-Based':>15} {'Collaborative':>15}")
        print("-"*50)
        for metric in ['precision@k', 'recall@k', 'ndcg@k', 'coverage']:
            cb = content_metrics.get(metric, 0)
            cf = collab_metrics.get(metric, 0)
            print(f"{metric:<20} {cb:>15.4f} {cf:>15.4f}")

        if 'diversity' in content_metrics:
            print(f"{'diversity':<20} {content_metrics['diversity']:>15.4f} {'N/A':>15}")

        print("="*60)

        return results


if __name__ == "__main__":
    evaluator = RecommenderEvaluator()
    evaluator.run_full_evaluation(k=10)
