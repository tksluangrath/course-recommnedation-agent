# Setup & Usage Instructions

Complete guide to getting the Course Advisor running from scratch on a new machine.

---

## Option A — Docker (recommended)

The fastest way to run the project. No Python, no Ollama, no manual pipeline steps.

**Requirements:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (free)

```bash
# 1. Clone the repo
git clone https://github.com/tksluangrath/course-recommnedation-agent.git
cd course-recommnedation-agent

# 2. Copy environment file
cp .env.template .env

# 3. Start everything
docker compose up --build
```

The first run downloads Llama 3.1 (~4.7 GB) and builds the Python image — this takes a few minutes. Subsequent runs start in seconds.

Open [http://localhost:8501](http://localhost:8501) in your browser.

**Stop the app:**
```bash
docker compose down
```

**Restart (no rebuild needed):**
```bash
docker compose up
```

---

## Option B — Manual Setup

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.9–3.12 | 3.13 works with the torch workaround noted below |
| Ollama | Latest | Local LLM runtime — free, runs offline |
| Git | Any | For cloning |
| RAM | 8 GB minimum | 16 GB recommended for running llama3.1 |
| Disk | ~12 GB free | Model (~4.7 GB) + embeddings + DB |

### 1. Clone the Repo

```bash
git clone https://github.com/tksluangrath/course-recommnedation-agent.git
cd course-recommnedation-agent
```

### 2. Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs: LangChain, Streamlit, ChromaDB, sentence-transformers, SQLAlchemy, NetworkX, Plotly, pandas, and all other required packages.

> **Windows + Python 3.13 note:** If you see a PyTorch DLL error on first import, add `import torch` as the very first line of any script that uses sentence-transformers. The CLI and Streamlit app already handle this automatically.

### 4. Install Ollama and Download the Model

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

> **Using Claude instead of Ollama:** Set `LLM_PROVIDER=claude` and `CLAUDE_API_KEY=your-key` in `.env`. The agent will use Claude instead of the local model.

### 5. Configure Environment Variables

```bash
cp .env.template .env
```

Open `.env` and set the following (all optional — the app runs on defaults):

```
# LLM provider: "ollama" (default, free) or "claude" (requires API key)
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1

# Only needed if LLM_PROVIDER=claude
CLAUDE_API_KEY=
CLAUDE_MODEL=claude-sonnet-4-20250514

# Only needed for live Coursera API data (optional)
COURSERA_CLIENT_ID=
COURSERA_CLIENT_SECRET=
```

### 6. Get the Course Data

The app uses the 2025 Coursera dataset from Kaggle (3,404 courses).

**Option A — Manual download:**
1. Download the dataset from [Kaggle](https://www.kaggle.com/datasets/yosefxx590/coursera-courses-and-skills-dataset-2025)
2. Place the CSV in `data/raw/` and rename it:
   ```
   data/raw/coursera_courses_2025.csv
   ```

**Option B — Automated download (requires Kaggle API key):**
```bash
python fetch_coursera_data.py
```

### 7. Initialize the Data Pipeline

Run these commands in order. Each takes ~30–60 seconds on first run.

```bash
# 1. Clean the raw CSV → data/processed/cleaned_courses.csv
python src/utils/data_cleaner.py

# 2. Create the SQLite database and load all courses + skills + prerequisites
python src/utils/load_data_to_db.py

# 3. Generate course embeddings → data/embeddings/chroma_db/
python src/utils/embeddings.py
```

After this you should have:
- `data/processed/cleaned_courses.csv` — 2,759 courses
- `data/courses.db` — SQLite with courses, skills, prerequisites, and user profiles
- `data/embeddings/chroma_db/` — vector index for semantic search

### 8. Run the App

**Streamlit Web UI:**
```bash
streamlit run app/streamlit_app.py
```
Opens at [http://localhost:8501](http://localhost:8501).

**Command-Line Interface:**
```bash
# Named user (profile persists between sessions)
python src/agents/chat_cli.py --user yourname

# Without a name (prompts on startup)
python src/agents/chat_cli.py
```

---

## Using the Web UI

### First-Time Setup

1. Open [http://localhost:8501](http://localhost:8501)
2. Enter a username and click **Start Learning**
3. In the sidebar, set up your profile:
   - **Add Skills** — comma-separated, e.g. `Python, SQL, Excel`
   - **Set Goal** — e.g. `Become a data scientist`
   - **Set Hours / Week** — how many hours you can study per week

### Chatting

Type any question in the chat box at the bottom. Examples:

| What you type | What happens |
|---|---|
| `What courses should I take for machine learning?` | Returns a ranked list of courses |
| `Create a learning path for data science` | Returns a Beginner→Advanced path + Gantt chart |
| `I have 8 hours a week, how long will it take?` | Returns a timeline with week-by-week schedule |
| `What do I need to learn before taking Deep Learning?` | Returns the prerequisite chain |
| `Analyze my skill gap for becoming a data engineer` | Returns missing skills in order + donut chart |
| `Find courses similar to Machine Learning by Andrew Ng` | Returns semantically similar courses |
| `What are the top skills in Data Science?` | Returns the most-taught skills by course count |

### Quick Actions (Sidebar)

- **Build Learning Path** — fill in goal + hours → sends the message automatically
- **Skill Gap Analysis** — fill in target role + current skills → sends the message automatically

### Browse Courses

Open the **Browse Courses** expander in the sidebar to filter the full 2,759-course catalog by category, difficulty, and minimum rating.

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

Profile changes persist to the database immediately and carry over to the next session.

---

## Troubleshooting

### Docker

**Containers won't start:**
```bash
docker compose down && docker compose up --build
```

**Model download stuck or timed out:**
Stop with `Ctrl+C`, then restart — the download resumes from where it left off in the named volume.

**Port 8501 already in use:**
Either stop the conflicting process or change the port in `docker-compose.yml`:
```yaml
ports:
  - "8502:8501"   # access at localhost:8502
```

**Reset everything (including downloaded model):**
```bash
docker compose down -v   # removes named volumes including the Ollama model cache
docker compose up --build
```

---

### Manual Setup

**"Ollama is not running" error:**
```bash
ollama serve
```
Keep this running in a separate terminal while using the app.

**"model not found" error:**
```bash
ollama pull llama3.1
```

**First query takes 10–20 seconds:**
Normal. The embedding model, ChromaDB, and collaborative filtering data all initialize on the first query. Subsequent queries are fast.

**PyTorch DLL error (Windows + Python 3.13):**
Add `import torch` as the very first import in any script. The CLI and Streamlit app already do this.

**ChromaDB is empty / no search results:**
```bash
python src/utils/embeddings.py
```

**Database errors / missing tables:**
```bash
python src/utils/load_data_to_db.py
```
This drops and recreates all tables. User profiles will be reset.

**Streamlit "DuplicateWidgetID" error:**
Stop with `Ctrl+C` and restart:
```bash
streamlit run app/streamlit_app.py
```

---

## Project Structure (Quick Reference)

```
course-recommnedation-agent/
├── app/
│   └── streamlit_app.py        ← Web UI entry point
├── data/
│   ├── raw/                    ← Place downloaded CSV here
│   ├── processed/              ← Cleaned CSV (auto-generated)
│   ├── courses.db              ← SQLite database (auto-generated)
│   └── embeddings/             ← ChromaDB vector store (auto-generated)
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
│       ├── database.py         ← SQLAlchemy ORM + ProfileManager
│       ├── embeddings.py       ← ChromaDB + sentence-transformers
│       ├── data_cleaner.py     ← CSV normalization + sample data
│       ├── load_data_to_db.py  ← DB initialization script
│       ├── llm_config.py       ← Ollama / Claude setup
│       ├── api_collectors.py   ← CourseraAPI + edX + YouTube collectors
│       └── api_config.py       ← API credential config
├── docs/
│   └── PHASE1_COMPLETE.md … PHASE7_COMPLETE.md
├── Dockerfile                  ← Python 3.11-slim app image
├── docker-compose.yml          ← Orchestrates app + ollama containers
├── docker-entrypoint.sh        ← Pulls model on first run, starts Streamlit
├── .env.template               ← Copy to .env and fill in
├── requirements.txt
└── README.md
```

---

## Re-initializing from Scratch

**Docker:**
```bash
docker compose down -v          # removes containers and volumes
docker compose up --build       # fresh start (re-downloads model)
```

**Manual:**
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

> **Note:** Deleting `courses.db` removes all saved user profiles.

---

## Quick Verification (Manual Setup)

After completing setup, run this to verify the full stack works:

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
