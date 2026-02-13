---
noteId: "883f1e5006f811f19003a775bfa91e67"
tags: []

---

# Quick Start Guide

## Phase 1 Complete! Now What?

You've successfully set up the foundation for your AI-powered course recommendation system. Here's how to use what you've built and move forward.

## What You Can Do Right Now

### 1. Get Real Course Data (Recommended)

Download the Coursera dataset to work with real data instead of the 20 sample courses:

```bash
# 1. Go to: https://www.kaggle.com/datasets/khusheekapoor/coursera-courses-dataset-2021
# 2. Download the Coursera.csv file
# 3. Place it in: data/raw/Coursera.csv

# 4. Then run:
cd "C:\Users\super\iCloudDrive\Documents\course-recommnedation-agent"
python -c "from src.utils.data_cleaner import DataCleaner; from src.utils.data_loader import DataLoader; loader = DataLoader(); df = loader.load_coursera_kaggle(); cleaner = DataCleaner(); clean_df = cleaner.clean_coursera_data('data/raw/Coursera.csv'); cleaner.save_cleaned_data(clean_df)"
python src/utils/load_data_to_db.py
```

### 2. Test Semantic Search

Search for courses using natural language:

```python
import pandas as pd
from src.utils.embeddings import EmbeddingManager

# Load data
df = pd.read_csv('data/processed/cleaned_courses.csv')

# Create embeddings
em = EmbeddingManager()
em.add_courses(df)

# Search!
results = em.search_courses("machine learning for beginners", n_results=5)
print(results[['course_name', 'difficulty_level', 'similarity_score']])

# Filter by difficulty
results = em.search_courses(
    "python programming",
    difficulty="Beginner",
    n_results=5
)
```

### 3. Query the Database

Use SQLAlchemy to query courses:

```python
from src.utils.database import DatabaseManager

db = DatabaseManager()

# Search by keywords
courses = db.search_courses(query="data science", limit=10)
for course in courses:
    print(f"{course.course_name} - {course.university}")

# Filter by difficulty and category
courses = db.search_courses(
    difficulty="Beginner",
    min_rating=4.5,
    limit=10
)

# Get database statistics
stats = db.get_stats()
print(f"Total courses: {stats['total_courses']}")
print(f"Difficulty breakdown: {stats['difficulty_distribution']}")
```

### 4. Test Your LLM

```bash
python src/utils/llm_config.py
```

This will show your current LLM configuration and test the connection.

## Move to Phase 2: Build Recommendation Algorithms

Now you're ready to build the actual recommendation engine. Here's what Phase 2 involves:

### Phase 2 Roadmap

1. **Content-Based Filtering** (Week 2-3)
   - Use the embeddings you've created
   - Recommend courses similar to one the user likes
   - Implement course similarity functions

2. **Collaborative Filtering** (Week 3-4)
   - User-user similarity
   - Item-item similarity
   - Handle the cold-start problem

3. **Hybrid Recommender** (Week 4)
   - Combine both approaches
   - Implement ranking

### What to Build Next

**Step 1**: Create `src/recommender/content_based.py`

This will use your embeddings to find similar courses:

```python
class ContentBasedRecommender:
    def __init__(self, embedding_manager, database_manager):
        self.em = embedding_manager
        self.db = database_manager

    def recommend_similar_courses(self, course_id, n_recommendations=5):
        """Recommend courses similar to the given course."""
        # Get course from database
        # Find similar courses using embeddings
        # Return recommendations
        pass

    def recommend_by_interests(self, interests, n_recommendations=10):
        """Recommend courses based on user interests/goals."""
        # Use semantic search on interests
        # Return top matches
        pass
```

**Step 2**: Create `src/recommender/collaborative.py`

This will use user interaction data:

```python
class CollaborativeRecommender:
    def __init__(self, database_manager):
        self.db = database_manager

    def recommend_by_user_similarity(self, user_id, n_recommendations=5):
        """Recommend based on similar users."""
        # Find users with similar course enrollments/ratings
        # Recommend courses they liked
        pass
```

**Step 3**: Create evaluation metrics

Create `src/recommender/evaluator.py` to measure how well your recommendations work.

## Useful Python Snippets

### Add a Single Course

```python
from src.utils.database import DatabaseManager

db = DatabaseManager()

course_data = {
    'course_name': 'Advanced Machine Learning',
    'university': 'MIT',
    'difficulty_level': 'Advanced',
    'course_rating': 4.9,
    'course_description': 'Deep dive into advanced ML algorithms...',
    'category': 'Machine Learning',
    'estimated_hours': 60.0
}

course = db.add_course(course_data)
print(f"Added: {course.course_name}")
```

### Simulate User Interaction

```python
from src.utils.database import DatabaseManager, UserInteraction
from sqlalchemy.orm import sessionmaker

db = DatabaseManager()
Session = sessionmaker(bind=db.engine)
session = Session()

interaction = UserInteraction(
    user_id="user123",
    course_id=1,
    interaction_type="enrolled",
    rating=4.5
)

session.add(interaction)
session.commit()
session.close()
```

### Export Data for Analysis

```python
import pandas as pd
from src.utils.database import DatabaseManager

db = DatabaseManager()

# Get all courses as a DataFrame
courses = db.get_all_courses()
df = pd.DataFrame([{
    'id': c.id,
    'name': c.course_name,
    'university': c.university,
    'difficulty': c.difficulty_level,
    'rating': c.course_rating,
    'category': c.category
} for c in courses])

df.to_csv('data/export_courses.csv', index=False)
```

## Common Tasks

### Reset Database

```bash
# Delete the database file
rm data/courses.db

# Recreate and reload
python src/utils/load_data_to_db.py
```

### Rebuild Embeddings

```python
from src.utils.embeddings import EmbeddingManager
import pandas as pd

em = EmbeddingManager()
em.clear_database()  # Clear existing

df = pd.read_csv('data/processed/cleaned_courses.csv')
em.add_courses(df)
```

### Check What's in ChromaDB

```python
from src.utils.embeddings import EmbeddingManager

em = EmbeddingManager()
stats = em.get_stats()
print(stats)
```

## Learning Resources for Phase 2

**Recommendation Systems:**
- "Building Recommender Systems with Python" (free online)
- Andrew Ng's Coursera course on Recommender Systems
- Surprise library documentation: https://surpriselib.com/

**Collaborative Filtering:**
- https://towardsdatascience.com/intro-to-recommender-systems-collaborative-filtering-64a238194a26

**Content-Based Filtering:**
- https://towardsdatascience.com/introduction-to-recommender-systems-1-971bd274f421

**Evaluation Metrics:**
- Precision@K, Recall@K
- NDCG (Normalized Discounted Cumulative Gain)
- Coverage and diversity

## Need Help?

- Check [PHASE1_COMPLETE.md](PHASE1_COMPLETE.md) for a full summary of what's been built
- Read the documentation in each Python file (they have detailed docstrings)
- Test individual components using the `if __name__ == "__main__"` blocks

## Next Steps Summary

1. Get real Coursera data from Kaggle (optional but recommended)
2. Start building content-based recommender in `src/recommender/`
3. Implement similarity functions using your embeddings
4. Test recommendations on sample users
5. Build collaborative filtering
6. Create evaluation metrics
7. Move to Phase 3: AI Agent

---

Good luck with Phase 2! You've built a solid foundation.
