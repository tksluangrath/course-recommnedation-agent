# Phase 4 — Learning Path Logic ✅

Phase 3 left the learning paths feeling a bit flat — courses were grouped into three buckets (Beginner / Intermediate / Advanced) but the order within each bucket was arbitrary, there were no prerequisite connections, and the timeline was just a rough hour-count with no structure. Phase 4 fixed all of that.

## Prerequisite graph

The database schema had a `course_prerequisites` table since Phase 1, but it was empty. Filling it by hand for 2,759 courses wasn't realistic, so a heuristic seeder was built instead.

The logic: for any two courses A and B in the same category where A's difficulty is lower than B's and they share at least 2 skills — A is a prerequisite for B. Each course gets at most 3 prerequisites to keep the graph sparse and readable. The seeder is idempotent, so it's safe to run again without creating duplicates.

**Result: 3,682 prerequisite relationships seeded across 2,759 courses.**

New `DatabaseManager` methods: `get_course_by_name`, `add_prerequisite`, `get_prerequisites`, `populate_prerequisites_heuristic`.

## `LearningPathGraph` (`src/recommender/path_graph.py`)

A new module that uses NetworkX to power three things:

**`sequence_within_level(courses_df)`** — given a set of courses at the same difficulty level, orders them so that skill-foundational courses come first. It builds a DAG where an edge from A → B means "A teaches the skills that B builds on," then runs topological sort. If the graph is cyclic or has no edges (e.g. all courses are completely unrelated), it falls back to sorting by rating.

**`estimate_timeline(path, hours_per_week)`** — takes the full path (all three levels) and produces a structured schedule:
```python
{
    'total_hours': 600.0,
    'weeks': 60.0,
    'hours_per_week': 10,
    'per_level': {'Beginner': {'count': 3, 'hours': 160.0}, ...},
    'schedule': [{'weeks': '1–16', 'level': 'Beginner', 'courses': [...]}, ...]
}
```

**`get_prerequisite_chain(course_name)`** — BFS backwards through the prerequisite graph from a target course, returning an ordered list of what to take first. Handles courses not in the DB gracefully.

## What changed in the existing code

`recommend_learning_path` in `content_based.py` now attaches `estimated_hours` to each course in the result and runs `sequence_within_level` before returning — so the ordering within each difficulty tier is meaningful rather than arbitrary.

`get_skill_gap` now returns missing skills in priority order, scored by the average difficulty of courses that teach each skill. Foundational skills come first — the ones where beginner-level courses exist show up before the ones only taught in advanced courses.

The hybrid recommender got a fix: `estimated_hours` was being dropped during collaborative re-ranking. It's now backed up before the merge and restored after.

## Two new agent tools

Bringing the total to 9:

**`estimate_learning_timeline`** — input is `"goal | hours_per_week"`. Returns the total hours, total weeks, and a week-by-week schedule with course names per phase. The output format triggers the Gantt chart in the web UI (Phase 6).

**`get_prerequisite_path`** — input is a course name. Returns the prerequisite chain in order from first-to-take to target course.

The system prompt was updated to tell the agent when to use these: if someone asks how long something takes, use `estimate_learning_timeline`. If they ask what to take before a course, use `get_prerequisite_path`.

## What the output looks like now

```
Learning Path: machine learning

--- Beginner ---
  1. Machine Learning Rock Star (SAS) — ~120 hrs
  2. Machine Learning (Multiple educators) — ~120 hrs
  3. Fundamentals of Machine Learning for Supply Chain (LearnQuest) — ~20 hrs

--- Timeline (8 hrs/week) ---
  Total: ~980.0 hrs  (~122.5 weeks)
  Weeks 1–32:  Beginner     (3 courses, ~260.0 hrs)
  Weeks 33–77: Intermediate (3 courses, ~360.0 hrs)
  Weeks 78–122: Advanced   (3 courses, ~360.0 hrs)
```

## Known issues

- **Large timelines:** Specializations (multi-course bundles) can report 100+ hours each. Phase 5 added product-type-aware defaults for courses with missing data, but Specializations with known hours still contribute their full length.
- **Same-category prerequisites only:** The seeder connects courses within the same category. It doesn't know that Statistics is a prerequisite for Machine Learning — those are different categories in the dataset.

## Files

**Created:**
- `src/recommender/path_graph.py` — `LearningPathGraph`

**Modified:**
- `src/utils/database.py` — 4 new prerequisite-related methods
- `src/recommender/content_based.py` — hour attachment, intra-level sequencing, skill priority ordering
- `src/recommender/hybrid.py` — preserve `estimated_hours` through re-ranking
- `src/tools/recommender_tools.py` — updated 3 tools, added 2 new tools
- `src/agents/course_advisor.py` — updated `SYSTEM_PROMPT`

---

**Next:** [Phase 5 — User Profiles](PHASE5_COMPLETE.md)
*Updated: February 2026*
