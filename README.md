# Course Recommendation Agent

A personal project combining recommendation systems and conversational AI. You tell it what you want to learn and what you already know — it builds a structured course roadmap with timelines, prerequisite chains, and skill gap analysis.

Think of it as a knowledgeable friend who's memorized every course on Coursera.

## Why I built this

I wanted to go beyond toy examples and build something that ties together recommendation systems (collaborative filtering, content-based approaches) and AI agents (LangChain, tool use, conversation memory) in a real-world context. I was also reading *Principles of Building AI Agents* at the time and wanted to actually apply those ideas, not just read about them.

## What it does

You chat with it naturally — "I want to get into machine learning, I already know Python" — and the agent figures out what to recommend. It calls the right tools on its own: semantic course search, skill gap analysis, prerequisite chains, week-by-week timeline estimation. Your skills and goals are saved between sessions so you don't have to re-introduce yourself every time.

The recommendation engine blends content-based filtering (sentence-transformer embeddings + ChromaDB) with collaborative filtering (item-item and user-user similarity), then routes everything through a LangChain agent backed by Llama 3.1 running locally via Ollama.

Dataset: 2,759 Coursera courses, 1,754 skills, 3,682 prerequisite relationships.

## Demo

```
$ python src/agents/chat_cli.py --user alice

Welcome back, alice!
  Goal       : become a data scientist
  Skills     : Python, SQL
  Study time : 8 hrs/week

You: Create a learning path. I already know Python and SQL.

Advisor: Here's your personalized learning path:

  Beginner (~160 hrs):
  • Applied Data Science (IBM) — ~20 hrs
  • Data Science Fundamentals (UC Irvine) — ~20 hrs
  • Data Literacy (Johns Hopkins) — ~120 hrs

  Intermediate (~200 hrs):
  • Applied Data Science with Python (University of Michigan) — ~20 hrs
  • Data Science at Scale (University of Washington) — ~80 hrs
  • Data Structures and Algorithms (UCSD) — ~100 hrs

  --- Timeline (8 hrs/week) ---
  Total: ~600 hrs (~75 weeks)
  Weeks 1–20:  Beginner     (3 courses, ~160 hrs)
  Weeks 21–45: Intermediate (3 courses, ~200 hrs)
  Weeks 46–75: Advanced     (3 courses, ~240 hrs)
```

There's also a Streamlit web app with the same functionality, inline Plotly charts, a profile editor, and a filterable course catalog.

## Running it

**Docker (easiest — no installs needed):**
```bash
git clone https://github.com/tksluangrath/course-recommnedation-agent.git
cd course-recommnedation-agent
cp .env.template .env
docker compose up --build
```
Open `http://localhost:8501`. First run downloads Llama 3.1 (~4.7 GB). Fast after that.

**Locally:**
```bash
# Install dependencies
pip install -r requirements.txt

# Pull the model (requires Ollama — https://ollama.com/)
ollama pull llama3.1

# Download the 2025 Coursera dataset from Kaggle and save as data/raw/coursera_courses_2025.csv
# https://www.kaggle.com/datasets/yosefxx590/coursera-courses-and-skills-dataset-2025

# Initialize the data pipeline
python src/utils/data_cleaner.py
python src/utils/load_data_to_db.py
python src/utils/embeddings.py

# Run
streamlit run app/streamlit_app.py
# or CLI:
python src/agents/chat_cli.py --user yourname
```

## Tech stack

- **LangChain** — agent framework with tool calling
- **Ollama + Llama 3.1** — local LLM inference (no API costs)
- **ChromaDB + sentence-transformers** — semantic search over course embeddings
- **SQLite + SQLAlchemy** — course data, prerequisite graph, user profiles
- **NetworkX** — topological course sequencing within difficulty tiers
- **Streamlit + Plotly** — web UI with inline Gantt and donut charts
- **Docker Compose** — containerized deployment

## Build log

Each phase has notes on what was built and the decisions behind it:

- [Phase 1 — Foundation](docs/PHASE1_COMPLETE.md)
- [Phase 2 — Recommendation Algorithms](docs/PHASE2_COMPLETE.md)
- [Phase 3 — AI Agent](docs/PHASE3_COMPLETE.md)
- [Phase 4 — Learning Path Logic](docs/PHASE4_COMPLETE.md)
- [Phase 5 — User Profiles](docs/PHASE5_COMPLETE.md)
- [Phase 6 — Web Interface](docs/PHASE6_COMPLETE.md)
- [Phase 7 — Docker](docs/PHASE7_COMPLETE.md)

## Known limitations

Timeline estimates can run large when the path includes Specializations — they're multi-course bundles that legitimately take 100+ hours. Prerequisite relationships are seeded heuristically (same category, shared skills), so cross-category dependencies like "Statistics before Machine Learning" aren't captured.

## License

MIT
