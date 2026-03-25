# Phase 2 — Recommendation Algorithms ✅

Phase 2 replaced the 20-course sample database with the real 2025 Coursera dataset and built three recommendation engines on top of it — content-based, collaborative, and a hybrid that blends both. It also added evaluation metrics to verify the recommendations were actually useful, not just technically functional.

## The data problem

The first thing that needed fixing was the data pipeline. The original cleaner was written for the 2021 Coursera dataset, which has a completely different schema. The 2025 dataset ships with pre-extracted skills in a `Gained Skills` column but no course descriptions — which is actually fine, since we can synthesize descriptions from the title, category, and skills for embedding purposes.

| 2025 column | Internal name |
|---|---|
| `Title` | `course_name` |
| `Institution` | `university` |
| `Level` | `difficulty_level` |
| `Rate` | `course_rating` |
| `Subject` | `category` |
| `Gained Skills` | `extracted_skills` |
| `Duration` | `estimated_hours` |
| `Learning Product` | `learning_product` |

After cleaning and deduplication: **2,759 courses, 1,754 skills, 38,204 skill-course links**.

## The three recommenders

### Content-based (`src/recommender/content_based.py`)

The main workhorse. It uses the sentence-transformer embeddings from Phase 1 — each course is a vector, and recommendations are nearest neighbors in that space.

Key methods:
- `recommend_by_interests(query, n, difficulty)` — natural language → course list
- `recommend_by_skills(target_skills, n, difficulty)` — find courses that teach specific skills, with fallback to semantic search when skill overlap is weak
- `recommend_learning_path(goal, current_skills, n_per_level)` — returns three separate DataFrames: Beginner, Intermediate, Advanced
- `get_skill_gap(goal_skills, current_skills)` — set difference between what you know and what you need

### Collaborative filtering (`src/recommender/collaborative.py`)

There aren't real user interaction logs, so this uses synthetic users: `generate_synthetic_users()` creates users with category preferences and realistic rating distributions, then `recommend_user_user()` does weighted-average recommendations based on the top-20 most similar users.

The item-item side builds a cosine similarity matrix on the 2,759 × 1,754 course-skill matrix. Given a course, it finds the most skill-similar courses in the catalog.

### Hybrid (`src/recommender/hybrid.py`)

Blends the two at 60% content / 40% collaborative. A `_diversify()` step limits how many courses from the same category appear in a single recommendation list, so you're not handed five variations of the same course.

## Evaluation (`src/recommender/evaluator.py`)

Standard IR metrics:
- `precision_at_k` — how many of the top-K results were actually relevant
- `recall_at_k` — how many relevant items were found in the top-K
- `ndcg_at_k` — like precision, but rewards finding things higher up the list
- `catalog_coverage` — what fraction of the full catalog ever surfaces in recommendations
- `diversity` — how spread across categories a recommendation list is

The `RecommenderEvaluator` class runs these across both content-based and collaborative systems in one shot with `run_full_evaluation()`.

## Test snapshots

Querying "machine learning" returned relevant ML/AI courses. "Web development with React" returned frontend courses. A learning path for "data science" produced plausible Beginner → Intermediate → Advanced sequences.

Top skills in the dataset: data analysis (446 courses), machine learning (310), Python (287), data science (241), SQL (198).

## Coursera API integration

`src/utils/api_collectors.py` uses OAuth2 client credentials to pull live course data directly from Coursera's catalog API. The main value here is real course descriptions — the Kaggle dataset doesn't have them, but the API does. A `merge_with_kaggle()` method deduplicates by course name and combines both sources.

## Files

**Created:**
- `src/recommender/content_based.py`
- `src/recommender/collaborative.py`
- `src/recommender/hybrid.py`
- `src/recommender/evaluator.py`

**Modified:**
- `src/utils/data_cleaner.py` — rewritten for 2025 schema
- `src/utils/database.py` — added `num_reviews` and `learning_product` columns
- `src/utils/load_data_to_db.py` — updated for new column names

---

**Next:** [Phase 3 — AI Agent](PHASE3_COMPLETE.md)
*Updated: February 2026*
