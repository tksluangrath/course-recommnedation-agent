# Course Recommendation System with AI Learning Path Planner

A personal project to build a smart course recommendation system that uses AI agents to help people plan their learning paths. Instead of just showing you random courses, it actually understands your goals and builds a structured learning plan.

## What is this?

I'm building a recommendation system that combines traditional ML algorithms with conversational AI. The main idea is to have an AI agent that acts like a learning advisor — you tell it what you want to learn, and it creates a personalized roadmap with courses in the right order, considering prerequisites and your current skill level.

Think of it as having a really knowledgeable friend who knows thousands of courses and can help you figure out the best path to your goals.

## Why I'm building this

I wanted to work on something that combines:
- Recommendation systems (collaborative filtering, content-based approaches)
- AI agents (using LangChain and local LLMs)
- Real-world application (helping people learn more effectively)

Plus, I'm reading "Principles of Building AI Agents 2nd Edition" and wanted to apply what I'm learning.

## Current Status

**Phases 1–3 Complete — AI Agent is live and functional**

- **Phase 1** ✅ — Data pipeline, semantic search, LLM integration (Ollama + llama3.1)
- **Phase 2** ✅ — Content-based, collaborative, and hybrid recommendation engines + Coursera API integration
- **Phase 3** ✅ — Conversational AI agent with 7 tools, conversation memory, CLI chat interface
- **Phase 4** 🔜 — Learning path logic (prerequisite chains, timeline estimation)
- **Phase 5** 🔜 — Multi-turn improvements, user feedback
- **Phase 6** 🔜 — Streamlit web interface

You can chat with the agent right now by running `python src/agents/chat_cli.py`.

## Features Built So Far

**AI Agent (Phase 3):**
- Chat with a course advisor in natural language
- Automatically selects the right tools (search, recommend, skill gap analysis, etc.)
- Builds Beginner → Intermediate → Advanced learning paths
- Remembers your conversation (last 10 exchanges per session)
- Explains why it's recommending certain courses

**Recommendation Engine (Phase 2):**
- Content-based filtering using sentence-transformer embeddings + ChromaDB
- Collaborative filtering (item-item similarity, user-user similarity with synthetic users)
- Hybrid blending (60% content + 40% collaborative) with diversity controls
- Skill gap analysis between current and target skills
- Evaluation metrics: Precision@K, Recall@K, NDCG@K, catalog coverage, diversity

**Data Pipeline (Phase 1 + 2):**
- 2025 Coursera dataset: 3,404 raw → 2,759 unique courses, 1,754 skills
- Coursera OAuth2 API integration for live course data
- SQLite database with course metadata, skills, and skill-course links
- ChromaDB vector store for semantic search

## Quick Start

### Prerequisites

- Python 3.9+
- At least 8GB RAM (for running the LLM locally)
- About 10GB free disk space

### Setup

1. Clone the repo
```bash
git clone https://github.com/tksluangrath/course-recommnedation-agent.git
cd course-recommnedation-agent
```

2. Create a virtual environment
```bash
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Mac/Linux
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Install Ollama and download the model
```bash
# Download from https://ollama.com/
ollama pull llama3.1
```

5. Configure environment
```bash
cp .env.template .env
# Edit .env — set COURSERA_CLIENT_ID and COURSERA_CLIENT_SECRET if you have API access
```

6. Get the course data

Download the 2025 Coursera dataset from Kaggle and place it in `data/raw/`:
```
data/raw/coursera_courses_2025.csv
```

7. Initialize the pipeline
```bash
python src/utils/data_cleaner.py
python src/utils/database.py
python src/utils/load_data_to_db.py
python src/utils/embeddings.py
```

8. Start the AI agent
```bash
python src/agents/chat_cli.py
```

### Example Agent Session

```
You: Create a learning path for becoming a data scientist. I already know Python and SQL.

Agent: Great foundation! Here's your personalized learning path:

  Beginner:
  • Applied Data Science (IBM) — covers core data science workflow
  • Data Science Fundamentals (UC Irvine)
  • Data Literacy (Johns Hopkins)

  Intermediate:
  • Data Science at Scale (University of Washington)
  • Applied Data Science with Python (University of Michigan)
  • Data Structures and Algorithms (UCSD)

  Advanced:
  • Google Business Intelligence
  • Google Advanced Data Analytics
  • Data Warehousing for Business Intelligence (University of Colorado)
```

## Quick Examples

**Chat with the agent programmatically:**
```python
import torch  # must be first on Windows + Python 3.13
from src.agents.course_advisor import CourseAdvisorAgent

agent = CourseAdvisorAgent()
response = agent.chat("What skills should I learn for machine learning?")
print(response)
```

**Use the recommendation engine directly:**
```python
import torch
from src.recommender.hybrid import HybridRecommender

rec = HybridRecommender()
results = rec.recommend("machine learning for beginners", n=5)
print(results[['course_name', 'difficulty_level', 'score']])
```

**Semantic search:**
```python
import torch
from src.utils.embeddings import EmbeddingManager

em = EmbeddingManager()
results = em.search_courses("deep learning with PyTorch", n_results=5)
print(results[['course_name', 'difficulty_level']])
```

## Project Structure

```
course-recommnedation-agent/
├── data/
│   ├── raw/                    # Downloaded datasets
│   ├── processed/              # Cleaned data
│   └── embeddings/             # ChromaDB vector store
│
├── src/
│   ├── agents/
│   │   ├── course_advisor.py   # CourseAdvisorAgent (LangChain v1.2)
│   │   └── chat_cli.py         # Terminal chat interface
│   ├── recommender/
│   │   ├── content_based.py    # Embedding-based recommender
│   │   ├── collaborative.py    # Item-item & user-user filtering
│   │   ├── hybrid.py           # 60/40 blended recommender
│   │   └── evaluator.py        # Precision/Recall/NDCG metrics
│   ├── tools/
│   │   └── recommender_tools.py  # 7 LangChain @tool functions
│   └── utils/
│       ├── data_cleaner.py     # 2025 dataset column mapping
│       ├── database.py         # SQLite ORM (SQLAlchemy)
│       ├── embeddings.py       # ChromaDB + sentence-transformers
│       ├── llm_config.py       # Ollama / Anthropic LLM setup
│       ├── coursera_api.py     # Coursera OAuth2 API collector
│       └── api_config.py       # API credential management
│
├── PHASE2_COMPLETE.md          # Phase 2 implementation notes
├── PHASE3_COMPLETE.md          # Phase 3 implementation notes
└── requirements.txt
```

## Agent Tools

The agent has 7 tools it can call autonomously:

| Tool | What it does |
|---|---|
| `search_courses` | Natural language course search |
| `find_similar_courses` | Find courses similar to a given one |
| `recommend_by_skills` | Recommend by target skill list |
| `create_learning_path` | Build Beginner → Advanced roadmap |
| `analyze_skill_gap` | Find missing skills for a goal |
| `get_course_info` | Detailed info about a specific course |
| `get_popular_skills` | Trending skills by category |

## Tech Stack

- **Python** — everything
- **LangChain v1.2** — agent framework (`create_agent` API)
- **Ollama + Llama 3.1** — local LLM inference, no API costs
- **langchain-ollama** — ChatOllama for tool-calling support
- **ChromaDB** — vector database for semantic search
- **sentence-transformers** (`all-MiniLM-L6-v2`) — course embeddings
- **SQLite + SQLAlchemy** — course metadata database
- **Coursera OAuth2 API** — live course data
- **Streamlit** — planned for Phase 6 web interface

## Roadmap

**Phase 1: Foundation** ✅
- Project setup, data pipeline, semantic search, LLM integration

**Phase 2: Recommendation Algorithms** ✅
- Content-based filtering, collaborative filtering, hybrid blending
- Evaluation metrics, Coursera API integration
- See [PHASE2_COMPLETE.md](PHASE2_COMPLETE.md)

**Phase 3: AI Agent** ✅
- LangChain agent with 7 tools, conversation memory, CLI interface
- See [PHASE3_COMPLETE.md](PHASE3_COMPLETE.md)

**Phase 4: Learning Path Logic** 🔜
- Prerequisite chains, skill graph modeling
- Skill gap analysis with course sequencing
- Timeline estimation from course hours

**Phase 5: Improvements** 🔜
- Better multi-turn conversations
- User feedback loop
- Preference persistence

**Phase 6: Web Interface** 🔜
- Streamlit chat UI
- Learning path visualization
- User profiles and progress tracking
- Export learning plans

## Known Issues

- **PyTorch DLL Loading (Windows + Python 3.13):** Scripts importing sentence-transformers must have `import torch` as the very first import. The CLI chat handles this automatically.
- **First query latency:** The first query initializes the embedding model, ChromaDB, and synthetic user data — this takes ~10–20 seconds. Subsequent queries are fast.

## About the Data

Using the Coursera 2025 dataset from Kaggle:
- 3,404 raw → 2,759 unique courses after deduplication
- 1,754 unique skills extracted from `Gained Skills` field
- 38,204 skill-course links
- Top skills: data analysis (446 courses), machine learning (310), Python (287), data science (241), SQL (198)

Also supports live data from the Coursera API (OAuth2 client credentials) which provides real course descriptions.

## Contributing

This is a learning project, but suggestions, issues, and PRs are welcome. I'm figuring things out as I go.

## Notes

- Running everything locally to avoid API costs
- Part of my research on AI in education (working with UVA's DART Lab)
- Learning about both recommendation systems and AI agents simultaneously

## License

MIT License — use it however you want

## Links

- [LangChain docs](https://python.langchain.com/)
- [Ollama](https://ollama.com/)
- [Dataset (Kaggle)](https://www.kaggle.com/datasets/khusheekapoor/coursera-courses-dataset-2021)

---

Last updated: February 18, 2026
Status: Active development — Phase 3 complete, Phase 4 up next
