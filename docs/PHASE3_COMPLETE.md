# Phase 3 — AI Agent ✅

Phase 3 is where the project stopped being a recommendation library and became something you could actually talk to. A conversational AI agent was built using LangChain v1.2 + Ollama (Llama 3.1), wrapping all the Phase 2 recommendation engines as tools the agent can call on its own.

## How it works

The agent is a tool-calling LLM. You send it a natural language message, it decides which tools to use (if any), calls them in sequence, reads the results, and writes back a helpful response. You never have to think about which function to call — that's the whole point.

LangChain's `create_agent` API handles the reasoning loop. The LLM is `ChatOllama` (needed for tool-calling support, as opposed to the plain `Ollama` completion model used in Phase 1). Each tool is a `@tool`-decorated Python function with a clear docstring so the LLM understands when to use it.

## The 7 tools

All tools live in `src/tools/recommender_tools.py` and call into the Phase 2 recommenders:

| Tool | What you'd say to trigger it | Backend |
|---|---|---|
| `search_courses` | "Find me courses about data visualization" | `HybridRecommender.recommend()` |
| `find_similar_courses` | "What's similar to this course?" | `ContentBasedRecommender.recommend_similar()` |
| `recommend_by_skills` | "I want to learn pandas, dask, and SQL" | `ContentBasedRecommender.recommend_by_skills()` |
| `create_learning_path` | "Build me a learning path for becoming a data scientist" | `HybridRecommender.recommend_learning_path()` |
| `analyze_skill_gap` | "What do I need to learn to become a ML engineer?" | `ContentBasedRecommender.get_skill_gap()` |
| `get_course_info` | "Tell me about the Google Data Analytics course" | `DatabaseManager.search_courses()` |
| `get_popular_skills` | "What skills are trending in data science?" | `ContentBasedRecommender.get_popular_skills()` |

Each tool formats its output as readable text so the LLM can incorporate it naturally into its response without extra parsing.

## The agent class

`CourseAdvisorAgent` in `src/agents/course_advisor.py`:
- Takes a `user_id` and loads that user's profile on startup (this became important in Phase 5)
- Holds per-session conversation history (last 10 exchanges) — the LLM has context for follow-ups
- Has a system prompt that sets the "learning advisor" persona: explain recommendations, ask clarifying questions, tailor advice to skill level
- Handles errors gracefully — if a tool call fails, it returns a readable message instead of crashing
- Multiple sessions can run concurrently (each has its own history)

## The CLI

`src/agents/chat_cli.py` is a terminal chat loop built for testing and actual use:

```bash
python src/agents/chat_cli.py --user alice
```

Commands available mid-chat: `/quit`, `/reset`, `/history`. Ctrl+C exits cleanly.

## What the agent actually said

**Test 1 — popular skills:**
- Input: "What are the top 5 popular skills in Data Science?"
- The agent called `get_popular_skills` with `category="Data Science"`, got back data analysis (371), machine learning (233), data manipulation (186), applied machine learning (174), data visualization software (168), and then explained *why* each of those matters for a data science career.

**Test 2 — learning path:**
- Input: "Create a learning path for becoming a data scientist. I already know Python and SQL."
- The agent called `create_learning_path`, got back a structured three-level path, and presented it clearly with the reasoning behind the progression.

The agent doesn't just dump the tool output — it adds context, which is the part that makes it actually useful.

## Known issues at this point

- **First query latency:** ~10–20 seconds the first time, while ChromaDB, the embedding model, and synthetic user data all initialize. Fast after that.
- **PyTorch DLL (Windows + Python 3.13):** `import torch` must be the first import in any script that uses sentence-transformers. The CLI handles this automatically.

## Files

**Created:**
- `src/tools/recommender_tools.py` — 7 LangChain tools
- `src/agents/course_advisor.py` — `CourseAdvisorAgent`
- `src/agents/chat_cli.py` — terminal chat interface

**Modified:**
- `src/utils/llm_config.py` — added `get_chat_llm()` returning a `ChatOllama` or `ChatAnthropic` instance (the plain completion model can't do tool calling)
- `requirements.txt` — added `langchain-ollama>=0.1.0`

---

**Next:** [Phase 4 — Learning Path Logic](PHASE4_COMPLETE.md)
*Updated: February 2026*
