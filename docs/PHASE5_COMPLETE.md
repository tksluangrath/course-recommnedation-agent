# Phase 5 — User Profiles & Smarter Timelines ✅

Two things were frustrating about the agent at the end of Phase 4. First, you had to re-introduce yourself every session — "I know Python and SQL, I want to become a data scientist" — because nothing persisted between runs. Second, timeline estimates were all over the place because the fallback when a course was missing its hour count was always 20h, whether that course was a 2-hour guided project or a 6-month specialization.

Phase 5 fixed both.

## User profiles

### The database model

A `UserProfile` table was added to SQLite with the columns that matter for personalization:

| Column | What it stores |
|---|---|
| `user_id` | Username (primary key) |
| `known_skills` | JSON array of skill strings |
| `goals` | Free-text learning goal |
| `hours_per_week` | Weekly study hours (default: 10.0) |
| `preferred_difficulty` | Optional difficulty preference |
| `created_at` / `updated_at` | Timestamps |

`known_skills` is stored as JSON under the hood but always serializes/deserializes automatically — callers get a plain `List[str]` and never have to think about it.

Three new `DatabaseManager` methods: `get_profile`, `get_or_create_profile`, `update_profile`.

### Profile injection

The important part isn't just storing the profile — it's making sure the agent actually uses it. Every time you send a message, `CourseAdvisorAgent.chat()` prepends a `SystemMessage` with a one-liner like:

```
User profile — Known skills: Python, SQL, Pandas | Goal: become a data scientist | 8 hrs/week
```

This means the agent always has context. You can ask "what should I learn next?" without restating your background, and it gives you a personalized answer instead of a generic one.

The user's `hours_per_week` is also wired directly into the tools module via `set_active_profile()`, so learning path timelines automatically use the right study pace without you having to type `| 8` every time.

### CLI profile commands

The CLI got a rewrite to support user-aware sessions:

```bash
python src/agents/chat_cli.py --user alice
```

Returning users see a personalized greeting:
```
Welcome back, alice!
  Goal       : become a data scientist
  Skills     : Python, SQL, Pandas
  Study time : 8 hrs/week
```

New users get a setup prompt instead.

Commands available mid-chat:

| Command | What it does |
|---|---|
| `/profile` | Print the full saved profile |
| `/skills Python, R, dbt` | Add skills (persisted immediately) |
| `/goal become a ML engineer` | Update the learning goal |
| `/hours 8` | Set weekly study hours |
| `/quit` | Show a profile summary and exit |

## Smarter timeline defaults

The flat `fillna(20.0)` approach in `estimate_timeline` meant a 2-hour Guided Project and a 100-hour Specialization were treated identically when their hour field was missing. That's obviously wrong.

Phase 5 replaced the fallback with a lookup table:

| Product type | Default hours |
|---|---|
| Guided Project | 2 |
| Course | 20 |
| Specialization | 100 |
| Professional Certificate | 100 |
| (anything else) | 20 |

A new `_resolve_hours(row)` method checks the actual `estimated_hours` field first. If it's missing or NaN, it falls back to the product-type default. The `learning_product` column is now propagated all the way through `_attach_hours` in the content-based recommender so it's always available when needed.

**Concrete improvement:** a path with 2 Guided Projects + 1 Course + 1 Specialization now estimates `2 + 2 + 20 + 100 = 124h` instead of the wrong `20 × 4 = 80h`.

## Files changed

| File | What changed |
|---|---|
| `src/utils/database.py` | `UserProfile` model + 3 profile CRUD methods |
| `src/agents/course_advisor.py` | `user_id` support, `SystemMessage` profile injection, profile pass-through methods |
| `src/agents/chat_cli.py` | Full rewrite — username arg, personalized greeting, 4 new slash commands |
| `src/recommender/path_graph.py` | `PRODUCT_HOUR_DEFAULTS`, `_resolve_hours()`, smarter `estimate_timeline` |
| `src/recommender/content_based.py` | `_attach_hours` now also propagates `learning_product` |
| `src/tools/recommender_tools.py` | `set_active_profile()`, profile hours wired into timeline tools |

No existing tool signatures or agent API methods changed — everything in Phases 1–4 continued to work unchanged.

---

**Next:** [Phase 6 — Web Interface](PHASE6_COMPLETE.md)
*Updated: February 2026*
