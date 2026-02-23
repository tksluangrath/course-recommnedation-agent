# Phase 5 Complete — User Profile Persistence & Smarter Timelines

## Summary

Phase 5 added two major improvements to the Course Advisor agent:

1. **User profile persistence** — users now have a saved profile (skills, goal, study hours) that persists across CLI sessions in SQLite and is automatically injected into every agent conversation turn.
2. **Smarter timeline defaults** — replaced the flat 20-hour fallback with product-type-aware defaults so Guided Projects, Courses, Specializations, and Professional Certificates each get realistic hour estimates.

---

## What Was Built

### 1. `UserProfile` Database Model

**File:** `src/utils/database.py`

Added a new SQLAlchemy model with its own table:

| Column | Type | Description |
|---|---|---|
| `user_id` | String (PK) | Username — primary key |
| `known_skills` | Text | JSON array of skill strings |
| `goals` | Text | Free-text learning goal |
| `hours_per_week` | Float | Available study hours per week (default: 10.0) |
| `preferred_difficulty` | String | Optional difficulty preference |
| `created_at` / `updated_at` | DateTime | Timestamps |

Three new `DatabaseManager` methods: `get_profile`, `get_or_create_profile`, `update_profile`.
`known_skills` is stored as a JSON string and automatically serialized/deserialized so callers always work with `List[str]`.

---

### 2. `ProfileManager` — New Module

**File:** `src/utils/profile_manager.py`

A clean wrapper over `DatabaseManager` that owns all profile operations:

| Method | Description |
|---|---|
| `load(user_id)` | Returns profile as a plain dict |
| `save(user_id, profile)` | Writes back to SQLite |
| `add_skills(user_id, new_skills)` | Merges + deduplicates skills, returns updated list |
| `get_context_string(user_id)` | Formats one-liner for agent system prompt injection |
| `format_display(user_id)` | Multi-line profile display for `/profile` command |

**Context string example:**
```
User profile — Known skills: Python, SQL, Pandas | Goal: become a data scientist | 8 hrs/week
```

---

### 3. Agent Profile Integration

**File:** `src/agents/course_advisor.py`

- `__init__` now accepts `user_id: str` and loads the profile from SQLite on startup.
- `chat()` prepends a `SystemMessage` with the profile context string before every conversation turn — the agent always knows the user's skills and goal without the user having to repeat them.
- Added pass-through methods: `get_profile()`, `update_profile(**kwargs)`, `add_skills(skills)`, `display_profile()`.
- Profile `hours_per_week` is wired into the tools module via `set_active_profile()` so timelines automatically use the user's preferred study pace.

---

### 4. CLI Profile Commands

**File:** `src/agents/chat_cli.py`

Complete rewrite to support user-aware sessions:

**Startup:**
- `--user <name>` CLI argument (e.g., `python chat_cli.py --user alice`) or interactive prompt.
- Personalized greeting for returning users showing their goal, top skills, and study hours.
- Fresh users get a setup prompt.

**New slash commands:**

| Command | Description |
|---|---|
| `/profile` | Display the full saved profile |
| `/skills Python, SQL, R` | Add skills (persisted immediately) |
| `/goal become a ML engineer` | Set/update learning goal |
| `/hours 8` | Set available study hours per week |
| `/quit` | Show profile summary and exit |

**Example session:**
```
$ python src/agents/chat_cli.py --user alice

Welcome back, alice!
  Goal       : become a data scientist
  Skills     : Python, SQL, Pandas
  Study time : 8 hrs/week

You: what should I learn next?
Advisor: Given your Python, SQL, and Pandas background, I'd recommend...
```

---

### 5. Product-Type-Aware Timeline Defaults

**File:** `src/recommender/path_graph.py`

Replaced the flat `fillna(20.0)` fallback with realistic defaults per course type:

| Product Type | Default Hours |
|---|---|
| Guided Project | 2 |
| Course | 20 |
| Specialization | 100 |
| Professional Certificate | 100 |
| (unknown) | 20 |

New `_resolve_hours(row)` static method checks `estimated_hours` first; if missing or NaN, looks up the product-type default. `estimate_timeline` now calls this per-row instead of summing after `fillna`.

**Result:** A path with 2 Guided Projects + 1 Course + 1 Specialization now estimates `2+2+20+100 = 124h` instead of the incorrect `20×4 = 80h`.

---

### 6. `learning_product` Propagated Through Pipeline

**File:** `src/recommender/content_based.py`

`_attach_hours` was updated to attach both `estimated_hours` and `learning_product` from the cleaned CSV so that `_resolve_hours` always has the product type available for fallback:

```python
for col in ['estimated_hours', 'learning_product']:
    col_map = self.courses_df.set_index('course_name')[col].to_dict()
    df[col] = df['course_name'].map(col_map)
```

---

### 7. Profile `hours_per_week` Wired Into Tools

**File:** `src/tools/recommender_tools.py`

Added module-level `_active_profile` global and `set_active_profile(profile)` function. Both `create_learning_path` and `estimate_learning_timeline` now read `_active_profile.get('hours_per_week', 10.0)` as the default study pace — no need for the user to type `| 8` every time if they've set `/hours 8` in their profile.

---

## Files Changed

| File | Change Type | Summary |
|---|---|---|
| `src/utils/database.py` | Modified | `UserProfile` model + `get_profile`, `get_or_create_profile`, `update_profile` |
| `src/utils/profile_manager.py` | **Created** | `ProfileManager` — load/save/add_skills/context_string/display |
| `src/agents/course_advisor.py` | Modified | `user_id` support, `SystemMessage` profile injection, pass-through methods |
| `src/agents/chat_cli.py` | Rewritten | Username prompt, personalized greeting, 4 new profile commands |
| `src/recommender/path_graph.py` | Modified | `PRODUCT_HOUR_DEFAULTS`, `_resolve_hours()`, smarter `estimate_timeline` |
| `src/recommender/content_based.py` | Modified | `_attach_hours` now propagates `learning_product` |
| `src/tools/recommender_tools.py` | Modified | `set_active_profile()`, profile `hours_per_week` wired into timeline tools |

---

## Verification

| Test | Expected Outcome |
|---|---|
| Start as "alice", `/skills Python, SQL`, `/hours 8`, quit. Restart as "alice". | Profile shown in greeting: skills + 8 hrs/week |
| Ask "what should I learn?" without stating skills. | Agent already knows skills from injected profile context |
| `estimate_learning_timeline.invoke("data science | 10")` | Guided Projects show ~2 hrs, Specializations ~100 hrs |
| Set `/hours 8`, ask for a learning path (no `| 8` in query). | Timeline block says "8 hrs/week" |
| Start as "bob" with different skills. | Bob's profile is independent of alice's |

---

## Phase 5 Stats

- **1 new module** created (`profile_manager.py`) — later consolidated into `database.py` during file cleanup
- **1 new database table** (`user_profiles`)
- **3 new profile CRUD methods** on `DatabaseManager`
- **5 new CLI commands** (`/profile`, `/skills`, `/goal`, `/hours`, improved `/quit`)
- **Product-type-aware timeline** replaces flat 20h default across all paths
- **Zero breaking changes** — all existing tool signatures and agent API preserved

---

**Status**: Phase 5 Complete
**Next Phase**: Phase 6 Complete — see [PHASE6_COMPLETE.md](PHASE6_COMPLETE.md)
**Updated**: February 2026
