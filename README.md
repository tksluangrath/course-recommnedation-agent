# Course Recommendation System with AI Learning Path Planner

A personal project to build a smart course recommendation system that uses AI agents to help people plan their learning paths. Instead of just showing you random courses, it actually understands your goals and builds a structured learning plan.

## What is this?

I'm building a recommendation system that combines traditional ML algorithms with conversational AI. The main idea is to have an AI agent that acts like a learning advisor - you tell it what you want to learn, and it creates a personalized roadmap with courses in the right order, considering prerequisites and your current skill level.

Think of it as having a really knowledgeable friend who knows thousands of courses and can help you figure out the best path to your goals.

## Why I'm building this

I wanted to work on something that combines:
- Recommendation systems (collaborative filtering, content-based approaches)
- AI agents (using LangChain and local LLMs)
- Real-world application (helping people learn more effectively)

Plus, I'm reading "Principles of Building AI Agents 2nd Edition" and wanted to apply what I'm learning.

## Current Status

**Phase 1 - Foundation (In Progress)**

Right now I'm setting up the basics:
- Got the project structure set up
- Downloaded and cleaned a dataset of ~4,000 Coursera courses
- Built semantic search using embeddings (you can search for courses in natural language)
- Set up Ollama to run Llama 3.1 locally (no API costs)
- Created a SQLite database to store everything

Next up is building the actual recommendation algorithms and then the AI agent.

## Features I'm Planning

**The AI Agent (main focus):**
- Chat with it like you would a learning advisor
- Tells you what you need to learn before taking advanced courses
- Creates a timeline based on how much time you have
- Explains why it's recommending certain courses
- Remembers your conversation and adapts to your needs

**Recommendation Engine:**
- Content-based filtering (find similar courses)
- Collaborative filtering (see what people with similar interests took)
- Handle the cold-start problem for new users

**Interface:**
- Simple chat interface (using Streamlit)
- Visualize your learning path
- Track progress
- Export your learning plan

## Tech Stack

I'm keeping this simple and free:

- Python for everything
- LangChain for building the agent
- Ollama + Llama 3.1 (runs on my machine, no cloud costs)
- ChromaDB for semantic search (stores course embeddings)
- SQLite for the database (might upgrade to PostgreSQL later)
- Streamlit for the web interface
- sentence-transformers for creating embeddings

## Project Structure

```
course-recommendation-agent/
├── data/
│   ├── raw/                    # Downloaded datasets
│   ├── processed/              # Cleaned data
│   └── embeddings/             # Vector embeddings
│
├── src/
│   ├── agents/                 # AI agent code
│   ├── recommender/            # Recommendation algorithms
│   ├── tools/                  # Tools the agent can use
│   └── utils/                  # Helper functions
│
├── app/                        # Streamlit web app
├── notebooks/                  # Jupyter notebooks for experiments
├── tests/                      # Unit tests
└── docs/                       # Documentation
```

## Getting Started

### What you need

- Python 3.9 or higher
- At least 8GB RAM (for running the LLM locally)
- About 10GB free disk space

### Setup

1. Clone the repo
```bash
git clone https://github.com/yourusername/course-recommendation-agent.git
cd course-recommendation-agent
```

2. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Install Ollama and download the model
```bash
# Mac/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Download Llama 3.1
ollama pull llama3.1

# Test it
ollama run llama3.1 "Hello!"
```

5. Get the course data

Download the Coursera dataset from Kaggle and put it in `data/raw/`:
https://www.kaggle.com/datasets/khusheekapoor/coursera-courses-dataset-2021

6. Initialize everything
```bash
# Clean the data
python src/utils/data_cleaner.py

# Set up the database
python src/utils/database.py

# Generate embeddings for semantic search
python src/utils/embeddings.py
```

7. Test that it works
```bash
# Test the LLM
python src/utils/llm_config.py

# Try semantic search
python test_search.py
```

## Quick Examples

**Search for courses:**
```python
from src.utils.embeddings import EmbeddingManager

em = EmbeddingManager()
results = em.search_courses("machine learning for beginners", n_results=5)
print(results[['course_name', 'difficulty_level']])
```

**Query the database:**
```python
from src.utils.database import DatabaseManager

db = DatabaseManager()
courses = db.search_courses("python", limit=10)
```

## Roadmap

**Phase 1: Foundation (Weeks 1-2)** - Current
- Project setup
- Data pipeline
- Semantic search
- LLM integration

**Phase 2: Basic Recommender (Weeks 2-3)**
- Content-based filtering
- Collaborative filtering
- Similarity calculations

**Phase 3: Build the Agent (Weeks 4-5)**
- Agent architecture
- Tool implementations
- Memory system
- Basic conversations

**Phase 4: Learning Path Logic (Weeks 5-6)**
- Prerequisite chains
- Skill gap analysis
- Path generation
- Timeline estimation

**Phase 5: Make it Better (Weeks 6-7)**
- Multi-turn conversations
- Better explanations
- User feedback
- Preferences

**Phase 6: Web Interface (Weeks 7-8)**
- Chat UI
- Visualizations
- User profiles
- Export features

## About the Data

Using the Coursera Courses dataset from Kaggle (2021):
- Around 4,000 courses
- Has course names, descriptions, difficulty levels, ratings
- I'm also extracting skills from descriptions

The database has:
- Course metadata
- Difficulty levels (Beginner/Intermediate/Advanced)
- Categories and skills
- Prerequisite relationships (will build this)

## Contributing

This is a learning project, but if you want to contribute or have ideas, feel free to open an issue or submit a PR. I'm figuring things out as I go, so suggestions are welcome.

## Notes

- Running everything locally to avoid API costs
- Using free tools and datasets
- Part of my research on AI in education (working with UVA's DART Lab)
- Learning about both recommendation systems and AI agents

## License

MIT License - use it however you want

## Links

- LangChain docs: https://python.langchain.com/
- Ollama: https://ollama.com/
- Dataset: https://kaggle.com/datasets/khusheekapoor/coursera-courses-dataset-2021

---

Last updated: February 9, 2026  
Status: Active development, Phase 1 in progress