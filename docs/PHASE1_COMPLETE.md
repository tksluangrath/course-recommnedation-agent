# Phase 1 — Foundation ✅

Phase 1 was about getting the plumbing in place before anything interesting could happen. No recommendation logic yet, no agent — just the infrastructure that everything else would eventually sit on top of.

## What got built

### Project skeleton

The folder structure was set up with placeholders for the pieces coming in later phases: `src/agents/` for the AI layer, `src/recommender/` for the ML engines, `src/tools/` for LangChain tool wrappers, and `src/utils/` for everything shared. Having clear separation from day one made it easier to add things later without reorganizing.

### LLM connection

`src/utils/llm_config.py` wraps both Ollama (local) and Claude (API) behind a single interface. Ollama + Llama 3.1 was the main setup — running locally means no API costs and no rate limits while experimenting.

### Database

SQLite via SQLAlchemy. The schema covers courses, skills, skill-course relationships, and a stub for user interactions (which came to life in Phase 5). Loading the initial 20 sample courses confirmed the pipeline worked end-to-end before dealing with the full dataset.

### Data pipeline

`data_cleaner.py` handles text normalization, difficulty standardization, skill extraction from descriptions, and category inference. Even on sample data it was useful to get this right early — the cleaning logic carried through to handling the full 3,404-course Coursera dataset in Phase 2.

### Semantic search

ChromaDB + `all-MiniLM-L6-v2` (sentence-transformers) for embedding generation and similarity search. On Windows + Python 3.13 there's a PyTorch DLL quirk where running scripts directly fails, but importing interactively works fine. The CLI chat in Phase 3 fixed this by ensuring `import torch` is always first.

## Where things stood after Phase 1

```
Courses in DB:     20 (sample data)
Skills extracted:  26
Categories:        Machine Learning, Data Science, Programming, Web Dev, Business, Cloud
```

This was enough to confirm the foundation held together. Phase 2 replaced the sample data with the real 2025 Coursera dataset and built the actual recommendation engines on top.

## Quick commands

```bash
# Clean and load data
python src/utils/data_cleaner.py
python src/utils/load_data_to_db.py

# Query the database
python -c "
from src.utils.database import DatabaseManager
db = DatabaseManager()
results = db.search_courses(query='machine learning', limit=5)
for course in results:
    print(f'{course.course_name} - {course.difficulty_level}')
"

# Test semantic search
python -c "
import pandas as pd
from src.utils.embeddings import EmbeddingManager
df = pd.read_csv('data/processed/cleaned_courses.csv')
em = EmbeddingManager()
em.add_courses(df)
results = em.search_courses('beginner python programming', n_results=5)
print(results[['course_name', 'difficulty_level', 'similarity_score']])
"
```

## Files

**Utilities:**
- `src/utils/llm_config.py` — LLM config (Ollama + Claude)
- `src/utils/database.py` — SQLite ORM
- `src/utils/embeddings.py` — ChromaDB + sentence-transformers
- `src/utils/data_cleaner.py` — data cleaning
- `src/utils/api_config.py` — API credential config
- `src/utils/load_data_to_db.py` — CSV → SQLite loader

**Data:**
- `data/raw/sample_courses.csv`
- `data/processed/cleaned_courses.csv`
- `data/courses.db`
- `data/embeddings/chroma_db/`

---

**Next:** [Phase 2 — Recommendation Algorithms](PHASE2_COMPLETE.md)
*Updated: February 2026*
