# Phase 4 Learning Path Logic - COMPLETE

## Summary

Phase 4 (Learning Path Logic) has been successfully completed. The flat three-bucket learning path structure from Phase 3 was upgraded with actual prerequisite-based course sequencing, per-course hour estimates, timeline planning, and two new agent tools — bringing the total to 9 tools.

## What Was Accomplished

### 1. Prerequisite Graph — Seeded and Queryable

**File:** [src/utils/database.py](src/utils/database.py)

The `course_prerequisites` table existed in the schema since Phase 1 but was completely empty. Phase 4 populates it heuristically and makes it queryable.

**New `DatabaseManager` methods:**

| Method | Description |
|---|---|
| `get_course_by_name(course_name)` | Exact + partial name lookup |
| `add_prerequisite(course_id, prereq_id)` | Insert a prerequisite edge |
| `get_prerequisites(course_id)` | Return all prerequisite courses for a given course |
| `populate_prerequisites_heuristic(min_shared_skills=2)` | Seed the table (run once) |

**Heuristic seeding logic:**
- For each pair of courses (A, B) in the same category where `A.difficulty < B.difficulty` and `len(A.skills ∩ B.skills) >= 2` → A is a prerequisite for B
- Difficulty order: Beginner=0, Mixed/Intermediate=1, Advanced=2
- Cap at 3 prerequisites per course to keep the graph sparse
- Idempotent — safe to run multiple times

**Result: 3,682 prerequisite relationships seeded across 2,759 courses**

---

### 2. New Module: `LearningPathGraph`

**File:** [src/recommender/path_graph.py](src/recommender/path_graph.py)

Uses `networkx` (already in `requirements.txt`) to power three capabilities:

#### `sequence_within_level(courses_df)`
Orders courses at the same difficulty level so skill-foundational courses come first:
- Builds a `nx.DiGraph` where edge A → B means "A's skills are a strict subset of B's skills" (A teaches what B builds on)
- Runs `nx.topological_sort` to produce the correct ordering
- Falls back to rating-descending sort if the graph has no edges or is cyclic

#### `estimate_timeline(path, hours_per_week=10.0)`
Sums `estimated_hours` across all levels and computes a week-by-week schedule:
```python
{
    'total_hours': 600.0,
    'weeks': 60.0,
    'hours_per_week': 10,
    'per_level': {'Beginner': {'count': 3, 'hours': 160.0}, ...},
    'schedule': [{'weeks': '1–16', 'level': 'Beginner', 'courses': [...]}, ...]
}
```

#### `get_prerequisite_chain(course_name)`
BFS traversal backwards through prerequisite edges from a target course:
- Returns an ordered list `[first-to-take, ..., target-course]`
- Handles courses not in the DB gracefully

---

### 3. Enhanced `recommend_learning_path`

**File:** [src/recommender/content_based.py](src/recommender/content_based.py)

Changes to `recommend_learning_path`:
- Added `_attach_hours()` helper that maps `estimated_hours` from the CSV onto any results DataFrame
- Each level DataFrame now includes `estimated_hours` per course
- After selecting top-N courses per level, calls `LearningPathGraph.sequence_within_level()` to order them by skill dependency

Changes to `get_skill_gap`:
- Added `_prioritize_skills()` helper that scores each missing skill by the average difficulty of courses that teach it
- Missing skills now returned in `priority_order` list with `{skill, level}` dicts ordered foundational-first

**File:** [src/recommender/hybrid.py](src/recommender/hybrid.py)
- Fixed: `estimated_hours` column was dropped during collaborative re-ranking; now backed up before merging and restored afterwards

---

### 4. Two New Agent Tools (9 total)

**File:** [src/tools/recommender_tools.py](src/tools/recommender_tools.py)

**Updated existing tools:**

- `_format_courses` — now renders `~N hrs` per course
- `create_learning_path` — accepts `"goal | hours_per_week"` format; shows hours per course and a timeline block at the end
- `analyze_skill_gap` — shows missing skills in priority order with level annotations (foundational/intermediate/advanced)

**New tools:**

| Tool | Input | Output |
|---|---|---|
| `estimate_learning_timeline` | `"goal \| hours_per_week"` | Total hours, total weeks, week-by-week schedule with course names |
| `get_prerequisite_path` | `course_name` | Ordered prerequisite chain from first-to-take to target |

---

### 5. Updated System Prompt

**File:** [src/agents/course_advisor.py](src/agents/course_advisor.py)

Added capabilities to `SYSTEM_PROMPT`:
- Estimate how long a learning path will take based on hours/week
- Show prerequisite courses required before a specific target course
- Sequence skills in foundational-first order

Added guidelines:
- When user asks how long something takes → use `estimate_learning_timeline`
- When user asks what to take before a course → use `get_prerequisite_path`
- When showing skill gaps → present in recommended learning order

---

## Test Results

**Timeline estimation:**
```
Input: "data science | 10"  (10 hrs/week)

Timeline Estimate: data science
  Studying 10 hours/week
  Total: ~600.0 hours (~60.0 weeks)

Week-by-week schedule:
  Weeks 1–16 — Beginner (3 courses, ~160.0 hrs)
    • Introduction to Data Science
    • Data Science for Business Innovation
    • Introduction to Data Management
  Weeks 17–36 — Intermediate (3 courses, ~200.0 hrs)
    • Applied Data Science Capstone
    • Data Science at Scale
    • Extract, Transform, and Load Data
  Weeks 37–60 — Advanced (3 courses, ~240.0 hrs)
    • Foundations of Data Science
    • Data Warehousing for Business Intelligence
    • Go Beyond the Numbers: Translate Data into Insights
```

**Skill gap with priority ordering:**
```
Input: goal_skills="machine learning, deep learning, python, statistics"
       current_skills="python"

Skill Gap Analysis
  Completion: 25%
  Skills you have: python

  Skills to learn (recommended order — foundational first):
    1. statistics — intermediate
    2. machine learning — intermediate
    3. deep learning — intermediate
```

**Learning path with hours and timeline (8 hrs/week):**
```
Learning Path: machine learning

--- Beginner ---
  1. Machine Learning Rock Star (by SAS) — ~120 hrs
  2. Machine Learning (by Multiple educators) — ~120 hrs
  3. Fundamentals of Machine Learning for Supply Chain (by LearnQuest) — ~20 hrs

--- Timeline (8 hrs/week) ---
  Total: ~980.0 hrs  (~122.5 weeks)
  Weeks 1–32: Beginner (3 courses, ~260.0 hrs)
  Weeks 33–77: Intermediate (3 courses, ~360.0 hrs)
  Weeks 78–122: Advanced (3 courses, ~360.0 hrs)
```

---

## Files Created

- [src/recommender/path_graph.py](src/recommender/path_graph.py) — `LearningPathGraph` (sequencing, timeline, prerequisite chain)

## Files Modified

- [src/utils/database.py](src/utils/database.py) — 4 new methods + prerequisite seeding
- [src/recommender/content_based.py](src/recommender/content_based.py) — `estimated_hours` in path output, intra-level sequencing, skill priority ordering
- [src/recommender/hybrid.py](src/recommender/hybrid.py) — preserve `estimated_hours` through re-ranking
- [src/tools/recommender_tools.py](src/tools/recommender_tools.py) — updated 3 tools, added 2 new tools (9 total)
- [src/agents/course_advisor.py](src/agents/course_advisor.py) — updated `SYSTEM_PROMPT`

## Known Issues

1. **Timeline hours can be large** — the Coursera dataset includes Specializations (multi-course bundles) which report 120+ estimated hours. This inflates timeline estimates. A future improvement would be to separate individual courses from specializations when doing timeline math.
2. **Prerequisite chain limited to seeded data** — the heuristic covers same-category pairs with shared skills. Cross-category prerequisites (e.g., "Statistics is a prerequisite for ML") are not captured because they are different categories in the dataset.
3. **PyTorch DLL** (Windows + Python 3.13) — `import torch` must be first. The agent CLI handles this automatically.

## Phase 5 Delivered

Phase 5 addressed the personalization and timeline accuracy gaps identified here:

| Planned | Delivered |
|---|---|
| User preference persistence | ✅ `UserProfile` SQLAlchemy model + `ProfileManager`; skills, goal, and hours/week saved to SQLite and loaded on startup |
| Better multi-turn context | ✅ Profile context injected as `SystemMessage` before every conversation turn — agent always knows user's skills and goal |
| Smarter timeline estimates | ✅ Product-type-aware defaults (Guided Project=2h, Course=20h, Specialization=100h) replace flat 20h fallback |
| Feedback loop ("I didn't like that") | ❌ Not implemented — deferred to Phase 6 or a future iteration |

See [PHASE5_COMPLETE.md](PHASE5_COMPLETE.md) for full details.

---

**Status**: Phase 4 Complete
**Next Phase**: Phase 5 Complete — see [PHASE5_COMPLETE.md](PHASE5_COMPLETE.md)
**Updated**: February 19, 2026
