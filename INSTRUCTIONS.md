---
noteId: "51484b000e7911f193f425dd705df8b0"
tags: []

---

# Setup & Usage Instructions

Complete guide to getting the Course Advisor running from scratch on a new machine.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.9–3.12 | 3.13 works with the torch workaround noted below |
| Ollama | Latest | Local LLM runtime — free, runs offline |
| Git | Any | For cloning |
| RAM | 8 GB minimum | 16 GB recommended for running llama3.1 |
| Disk | ~12 GB free | Model (~4.7 GB) + embeddings + DB |

---

## 1. Clone the Repo

```bash
git clone https://github.com/tksluangrath/course-recommnedation-agent.git
cd course-recommnedation-agent
```

---

## 2. Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs: LangChain, Streamlit, ChromaDB, sentence-transformers, SQLAlchemy, NetworkX, Plotly, pandas, and all other required packages.

> **Windows + Python 3.13 note:** If you see a PyTorch DLL error on first import, add `import torch` as the very first line of any script that uses sentence-transformers. The CLI and Streamlit app already handle this automatically.

---

## 4. Install Ollama and Download the Model

1. Download Ollama from [ollama.com](https://ollama.com/) and install it
2. Start the Ollama server:
   ```bash
   ollama serve
   ```
3. In a separate terminal, pull the model:
   ```bash
   ollama pull llama3.1
   ```
   This downloads ~4.7 GB. Only needed once.

> **Using Claude instead of Ollama:** If you have an Anthropic API key, set `LLM_PROVIDER=claude` and `ANTHROPIC_API_KEY=your-key` in `.env` (see Step 5). The agent will use Claude instead.

---

## 5. Configure Environment Variables

```bash
cp .env.template .env
```

Open `.env` and set the following (all are optional — the app runs without them):

```
# LLM provider: "ollama" (default, free) or "claude" (requires API key)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1

# Only needed if LLM_PROVIDER=claude
ANTHROPIC_API_KEY=

# Only needed for live Coursera API data (optional — Kaggle dataset works fine without this)
COURSERA_CLIENT_ID=
COURSERA_CLIENT_SECRET=
```

---

## 6. Get the Course Data

The app uses the 2025 Coursera dataset from Kaggle (3,404 courses).

**Option A — Manual download (recommended):**
1. Go to [kaggle.com](https://www.kaggle.com) and download the Coursera 2025 dataset
2. Place the CSV in `data/raw/` and rename it:
   ```
   data/raw/coursera_courses_2025.csv
   ```

**Option B — Automated download (requires Kaggle API key):**
```bash
python fetch_coursera_data.py
```

---

## 7. Initialize the Data Pipeline

Run these four commands in order. Each takes ~30–60 seconds on first run.

```bash
# 1. Clean the raw CSV and produce data/processed/cleaned_courses.csv
python src/utils/data_cleaner.py

# 2. Create the SQLite database and load all courses + skills
python src/utils/load_data_to_db.py

# 3. Seed the prerequisite relationships (3,682 edges heuristically)
#    This runs automatically inside load_data_to_db.py — no separate step needed

# 4. Generate course embeddings and store in ChromaDB
python src/utils/embeddings.py
```

After this you should have:
- `data/processed/cleaned_courses.csv` — 2,759 courses
- `data/courses.db` — SQLite database with courses, skills, prerequisites, and user profiles
- `data/embeddings/chroma_db/` — vector index for semantic search

---

## 8. Run the App

### Streamlit Web UI (recommended)

```bash
streamlit run app/streamlit_app.py
```

Opens at [http://localhost:8501](http://localhost:8501). Enter a username to start.

### Command-Line Interface

```bash
# Start with a named user (profile persists between sessions)
python src/agents/chat_cli.py --user yourname

# Or start without a name (prompts on startup)
python src/agents/chat_cli.py
```

---

## Using the Web UI

### First-Time Setup

1. Open [http://localhost:8501](http://localhost:8501)
2. Enter a username and click **Start Learning**
3. In the sidebar, use the edit forms to set up your profile:
   - **Add Skills** — comma-separated, e.g. `Python, SQL, Excel`
   - **Set Goal** — e.g. `Become a data scientist`
   - **Set Hours / Week** — how many hours you can study per week

### Chatting

Type any question in the chat box at the bottom. Examples:

| What you type | What happens |
|---|---|
| `What courses should I take for machine learning?` | Returns a ranked list of courses |
| `Create a learning path for data science` | Returns a Beginner→Advanced path + Gantt chart |
| `I have 8 hours a week, how long will it take?` | Returns a timeline estimate with week-by-week schedule |
| `What do I need to learn before taking Deep Learning?` | Returns the prerequisite chain |
| `Analyze my skill gap for becoming a data engineer` | Returns missing skills in order + donut chart |
| `Find courses similar to Machine Learning by Andrew Ng` | Returns semantically similar courses |
| `What are the top skills in Data Science?` | Returns the most-taught skills by course count |

### Quick Actions (Sidebar)

Use the sidebar shortcuts if you want structured output with charts:
- **Build Learning Path** — fill in goal + hours → sends the message for you
- **Skill Gap Analysis** — fill in target role + current skills → sends the message for you

### Browse Courses

Open the **Browse Courses** expander in the sidebar to explore the full catalog:
- Filter by category (Business / Computer Science / Data Science)
- Filter by difficulty (Beginner / Intermediate / Advanced / Mixed)
- Set a minimum rating threshold

---

## Using the CLI

```
/profile          — show your saved profile
/skills A, B, C  — add skills to your profile
/goal <text>      — set your learning goal
/hours <n>        — set available study hours/week
/history          — show conversation history
/reset            — clear conversation history
/quit             — save and exit
```

Profile changes (skills, goal, hours) persist to the database immediately and carry over to the next session.

---

## Troubleshooting

### "Ollama is not running" error
```bash
ollama serve
```
Keep this running in a separate terminal while using the app.

### "model not found" error
```bash
ollama pull llama3.1
```

### First query takes 10–20 seconds
Normal. The embedding model, ChromaDB, and collaborative filtering data all initialize on the first query. Subsequent queries are fast.

### PyTorch DLL error (Windows + Python 3.13)
Add `import torch` as the very first import in any script. The CLI and Streamlit app already do this.

### ChromaDB is empty / no search results
Re-run the embeddings step:
```bash
python src/utils/embeddings.py
```

### Database errors / missing tables
Re-run the database initialization:
```bash
python src/utils/load_data_to_db.py
```
This drops and recreates all tables. User profiles will be reset.

### Streamlit "DuplicateWidgetID" error
This can happen after a hot-reload during development. Stop the app with `Ctrl+C` and restart:
```bash
streamlit run app/streamlit_app.py
```

---

## Project Structure (Quick Reference)

```
course-recommnedation-agent/
├── app/
│   └── streamlit_app.py    ← Web UI entry point
├── data/
│   ├── raw/                ← Place downloaded CSV here
│   ├── processed/          ← Cleaned CSV (auto-generated)
│   ├── courses.db          ← SQLite database (auto-generated)
│   └── embeddings/         ← ChromaDB vector store (auto-generated)
├── src/
│   ├── agents/
│   │   ├── course_advisor.py   ← CourseAdvisorAgent class
│   │   └── chat_cli.py         ← CLI entry point
│   ├── recommender/
│   │   ├── content_based.py    ← Embedding-based recommendations
│   │   ├── collaborative.py    ← Collaborative filtering
│   │   ├── hybrid.py           ← 60/40 blended recommender
│   │   └── path_graph.py       ← Prerequisite graph + timeline
│   ├── tools/
│   │   └── recommender_tools.py  ← 9 LangChain agent tools
│   └── utils/
│       ├── database.py         ← SQLAlchemy ORM
│       ├── embeddings.py       ← ChromaDB + sentence-transformers
│       ├── data_cleaner.py     ← CSV normalization
│       ├── load_data_to_db.py  ← DB initialization script
│       ├── llm_config.py       ← Ollama / Claude setup
│       └── profile_manager.py  ← User profile CRUD
├── .env.template           ← Copy to .env and fill in
├── requirements.txt
└── README.md
```

---

## Re-initializing from Scratch

If something goes wrong or you want a clean slate:

```bash
# Delete generated data
rm data/courses.db
rm -rf data/processed/
rm -rf data/embeddings/

# Re-run the full pipeline
python src/utils/data_cleaner.py
python src/utils/load_data_to_db.py
python src/utils/embeddings.py
```

> **Note:** Deleting `courses.db` also removes all saved user profiles.

---

## Quick Verification

After completing setup, run this to verify everything works:

```bash
python -c "
import torch
import sys
sys.path.insert(0, 'src/agents')
sys.path.insert(0, 'src/utils')
sys.path.insert(0, 'src/tools')
sys.path.insert(0, 'src/recommender')
from course_advisor import CourseAdvisorAgent
agent = CourseAdvisorAgent(user_id='test')
print(agent.chat('What are the top 3 skills in Data Science?'))
"
```

If you see a list of skills, the full stack is working.
