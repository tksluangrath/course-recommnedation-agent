# Phase 2 Recommendation Algorithms - COMPLETE

## Summary

Phase 2 (Recommendation Algorithms) has been successfully completed. Four recommendation modules were built covering content-based filtering, collaborative filtering, hybrid blending, and evaluation metrics. The data pipeline was also updated to support the 2025 Coursera dataset.

## What Was Accomplished

### 1. Data Pipeline Updated for 2025 Dataset

The original pipeline expected the 2021 Coursera dataset columns. The 2025 dataset has a completely different schema:

| 2025 Column | Maps To |
|---|---|
| `Title` | `course_name` |
| `Institution` | `university` |
| `Level` | `difficulty_level` |
| `Rate` | `course_rating` |
| `Subject` | `category` |
| `Gained Skills` | `extracted_skills` |
| `Duration` | `estimated_hours` |
| `Reviews` | `num_reviews` |
| `Learning Product` | `learning_product` |

Key change: The 2025 dataset has no `course_description` field, but has rich `Gained Skills` data (pre-extracted, comma-separated). Synthetic descriptions are built from `title + category + skills` for embedding generation.

**Pipeline results:** 3,404 raw courses -> 2,759 unique courses, 1,754 skills, 38,204 skill-course links

### 2. Content-Based Recommender

**File:** [src/recommender/content_based.py](src/recommender/content_based.py)

Uses sentence-transformer embeddings stored in ChromaDB for semantic similarity search.

- `recommend_similar(course_name, n)` - find courses similar to a given course
- `recommend_by_interests(interests, n, difficulty)` - recommend based on natural language query
- `recommend_by_skills(target_skills, n, difficulty)` - recommend based on skill overlap with fallback to semantic search
- `recommend_learning_path(goal, current_skills, n_per_level)` - ordered Beginner/Intermediate/Advanced path
- `get_skill_gap(goal_skills, current_skills)` - gap analysis between current and target skills
- `get_popular_skills(category, top_n)` - most frequently taught skills

### 3. Collaborative Filtering Recommender

**File:** [src/recommender/collaborative.py](src/recommender/collaborative.py)

Item-item and user-user collaborative filtering using synthetic user interactions.

- `build_skill_matrix()` - sparse course-skill matrix (2759 courses x 1754 skills)
- `compute_item_similarity()` - cosine similarity on skill vectors
- `recommend_item_item(course_name, n)` - find similar courses by shared skills
- `generate_synthetic_users(n_users, seed)` - generate fake users with category preferences and realistic rating distributions
- `build_user_item_matrix(interactions_df)` - pivot table for user-item ratings
- `recommend_user_user(user_interactions, interactions_df, n)` - weighted average of top-20 similar users' ratings

### 4. Hybrid Recommender

**File:** [src/recommender/hybrid.py](src/recommender/hybrid.py)

Combines content-based and collaborative approaches with diversity controls.

- `recommend(query, user_history, n, difficulty)` - weighted hybrid scoring (60% content, 40% collaborative)
- `recommend_learning_path(goal, current_skills, user_history, n_per_level)` - personalized learning paths with collaborative boost
- `_diversify(df, n, max_per_category)` - limits courses per category to avoid monotony

### 5. Evaluation Metrics

**File:** [src/recommender/evaluator.py](src/recommender/evaluator.py)

Standard recommendation evaluation metrics.

- `precision_at_k()` - fraction of top-K recommendations that are relevant
- `recall_at_k()` - fraction of relevant items found in top-K
- `ndcg_at_k()` - Normalized Discounted Cumulative Gain (rewards higher-ranked hits)
- `catalog_coverage()` - fraction of catalog appearing in any recommendation
- `diversity()` - intra-list diversity based on category spread
- `RecommenderEvaluator` class with `evaluate_content_based()`, `evaluate_collaborative()`, `run_full_evaluation()`

## Test Results

**Content-Based** - "Machine Learning" query returned relevant ML/AI courses. "Web development with React" returned web development courses. Learning path for "data science" produced appropriate Beginner/Intermediate/Advanced courses.

**Collaborative Filtering** - Item-item similarity matrix (2759x1754) built successfully. Courses similar to "Machine Learning" returned relevant results. User-user filtering with synthetic data science preferences returned data science recommendations.

**Top Skills in Dataset:** data analysis (446 courses), machine learning (310), python (287), data science (241), SQL (198)

## Files Modified

- [src/utils/data_cleaner.py](src/utils/data_cleaner.py) - Rewritten for 2025 Coursera dataset column mapping
- [src/utils/database.py](src/utils/database.py) - Added `num_reviews` and `learning_product` columns to Course model
- [src/utils/load_data_to_db.py](src/utils/load_data_to_db.py) - Updated for new schema and column list

## Files Created

- [src/recommender/content_based.py](src/recommender/content_based.py) - Content-based recommendation engine
- [src/recommender/collaborative.py](src/recommender/collaborative.py) - Collaborative filtering engine
- [src/recommender/hybrid.py](src/recommender/hybrid.py) - Hybrid recommendation engine
- [src/recommender/evaluator.py](src/recommender/evaluator.py) - Evaluation metrics
- [src/utils/coursera_api.py](src/utils/coursera_api.py) - Coursera API collector with OAuth2

### 6. Coursera API Integration

**File:** [src/utils/coursera_api.py](src/utils/coursera_api.py)

Live API collector using OAuth2 client credentials to fetch courses directly from Coursera's catalog API.

- `authenticate()` - OAuth2 client credentials flow
- `fetch_all_courses(max_courses)` - paginated course fetching
- `fetch_partners()` - university/partner info
- `fetch_and_save()` - fetch and save to CSV
- `merge_with_kaggle()` - deduplicate and merge API data with Kaggle dataset

**Data sources:** Courses can now come from both the Kaggle 2025 dataset (3,404 courses with skills) AND the live Coursera API (which provides real descriptions). The merger deduplicates by course name.

## Known Issues

1. **PyTorch DLL Loading** (Windows + Python 3.13) - Scripts that import sentence-transformers need `import torch` as the first import, or run via `python -c "import torch; ..."`. This is a known PyTorch 2.10 issue on Windows.

## What's Next (Phase 3)

Phase 3 focuses on building the **AI Agent** using LangChain + Ollama:

1. **Agent Architecture** - ReAct-style agent with tool use
2. **Tool Implementations** - Search courses, recommend, build learning paths, skill gap analysis
3. **Memory System** - Conversation history and user preferences
4. **Basic Conversations** - Natural language interaction for course recommendations

---

**Status**: Phase 2 Complete
**Next Phase**: Phase 3 - AI Agent with LangChain
**Updated**: February 17, 2026
