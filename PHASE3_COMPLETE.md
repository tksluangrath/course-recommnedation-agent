---
noteId: "b4259ea00c7411f18adf3f60997cc249"
tags: []

---

# Phase 3 AI Agent - COMPLETE

## Summary

Phase 3 (AI Agent) has been successfully completed. A conversational course advisor agent was built using LangChain v1.2 + Ollama (llama3.1), with 7 tools wrapping the recommendation engines from Phase 2. The agent can search courses, build learning paths, analyze skill gaps, and maintain conversation history.

## What Was Accomplished

### 1. LLM ChatModel Support

**File:** [src/utils/llm_config.py](src/utils/llm_config.py)

Added `get_chat_llm()` method to `LLMConfig` that returns a ChatModel instance (required for LangChain tool calling):

- `ChatOllama` from `langchain-ollama` for local Ollama inference
- `ChatAnthropic` for Claude API (already supported)
- Backward compatible — existing `get_llm()` still works for non-agent use cases

### 2. Agent Tools

**File:** [src/tools/recommender_tools.py](src/tools/recommender_tools.py)

Seven LangChain `@tool` decorated functions that wrap the Phase 2 recommender methods. Each tool accepts string inputs, calls the appropriate backend, and returns formatted text for the LLM.

| Tool | Description | Backend Method |
|---|---|---|
| `search_courses` | Natural language course search | `HybridRecommender.recommend()` |
| `find_similar_courses` | Find courses similar to a given one | `ContentBasedRecommender.recommend_similar()` |
| `recommend_by_skills` | Recommend by target skills | `ContentBasedRecommender.recommend_by_skills()` |
| `create_learning_path` | Beginner-to-advanced learning plan | `HybridRecommender.recommend_learning_path()` |
| `analyze_skill_gap` | Gap analysis between current and goal skills | `ContentBasedRecommender.get_skill_gap()` |
| `get_course_info` | Detailed info about a specific course | `DatabaseManager.search_courses()` |
| `get_popular_skills` | Trending skills by category | `ContentBasedRecommender.get_popular_skills()` |

### 3. Course Advisor Agent

**File:** [src/agents/course_advisor.py](src/agents/course_advisor.py)

`CourseAdvisorAgent` class using LangChain v1.2 `create_agent` API:

- **LLM:** ChatOllama (llama3.1) or ChatAnthropic (Claude)
- **Architecture:** Tool-calling agent with automatic tool selection
- **System prompt:** Learning advisor persona that explains recommendations, asks clarifying questions, and considers user skill level
- **Memory:** Per-session conversation history (last 10 exchanges), supports multiple concurrent sessions
- **Error handling:** Graceful error recovery with user-friendly messages

Key methods:
- `chat(message, session_id)` — send message, get response
- `reset(session_id)` — clear conversation history
- `get_history(session_id)` — retrieve past messages

### 4. CLI Chat Interface

**File:** [src/agents/chat_cli.py](src/agents/chat_cli.py)

Terminal-based chat loop for interactive testing:

- Welcome message with capability overview
- `/quit` — exit the chat
- `/reset` — clear conversation history
- `/history` — show past messages
- Ctrl+C handling for clean exit

## Test Results

**Test 1: Popular Skills Query**
- Input: "What are the top 5 popular skills in Data Science?"
- Agent called `get_popular_skills` tool with category="Data Science"
- Returned: data analysis (371), machine learning (233), data manipulation (186), applied machine learning (174), data visualization software (168)
- Agent provided explanations for why each skill matters

**Test 2: Learning Path Creation**
- Input: "Create a learning path for becoming a data scientist. I already know Python and SQL."
- Agent called `create_learning_path` tool with goal and current skills
- Returned structured path:
  - Beginner: Applied Data Science (IBM), Data Science Fundamentals (UC Irvine), Data Literacy (Johns Hopkins)
  - Intermediate: Data Science at Scale (UW), Data Structures and Algorithms (UCSD), Applied Data Science with Python (Michigan)
  - Advanced: Google Business Intelligence, Data Warehousing (Colorado), Google Advanced Data Analytics

## Files Created

- [src/tools/recommender_tools.py](src/tools/recommender_tools.py) - 7 LangChain tools wrapping recommender methods
- [src/agents/course_advisor.py](src/agents/course_advisor.py) - CourseAdvisorAgent with conversation memory
- [src/agents/chat_cli.py](src/agents/chat_cli.py) - Terminal chat interface

## Files Modified

- [src/utils/llm_config.py](src/utils/llm_config.py) - Added `get_chat_llm()` and `ChatOllama` support
- [requirements.txt](requirements.txt) - Added `langchain-ollama>=0.1.0`
- [src/tools/__init__.py](src/tools/__init__.py) - Added exports
- [src/agents/__init__.py](src/agents/__init__.py) - Added exports

## Quick Start

```bash
# Start the chat interface
python src/agents/chat_cli.py

# Or test programmatically
python -c "
import torch
import sys
sys.path.insert(0, 'src/utils')
sys.path.insert(0, 'src/recommender')
sys.path.insert(0, 'src/tools')
sys.path.insert(0, 'src/agents')
from course_advisor import CourseAdvisorAgent
agent = CourseAdvisorAgent()
print(agent.chat('Recommend courses for learning web development'))
"
```

## Known Issues

1. **PyTorch DLL Loading** (Windows + Python 3.13) — when running scripts directly, `import torch` must come before sentence-transformers imports. The CLI chat handles this automatically.
2. **First query latency** — the first query takes longer as it initializes the embedding model, ChromaDB, and synthetic user data. Subsequent queries are fast.

## What's Next (Phase 4)

Phase 4 focuses on **Learning Path Logic**:

1. **Prerequisite chains** — model course dependencies
2. **Skill gap analysis** — deeper analysis with course sequencing
3. **Path generation** — optimal course ordering based on prerequisites
4. **Timeline estimation** — estimate completion time based on course hours

---

**Status**: Phase 3 Complete
**Next Phase**: Phase 4 - Learning Path Logic
**Updated**: February 17, 2026
