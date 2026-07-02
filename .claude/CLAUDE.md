# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Spendly** — a Flask + SQLite personal expense tracker. Users register, log in, record expenses (amount, category, date, description), and analyse spending. Project is being built step-by-step from a written spec; current state is the end of **Step 1 (database setup)** with all UI routes still placeholder.

Product brief lives in `README.md`. The authoritative build plan, schema, rules, and Definition of Done for each step live in `.claude/specs/NN-<step>.md` (e.g. `01-database-setup.md`). When a spec file exists for the step you are working on, follow it as the source of truth.

## Running the app

```
python app.py
```
- Listens on `http://127.0.0.1:5001` (debug mode, port is hardcoded in `app.py`).
- On import, `app.py` calls `init_db()` and `seed_db()` inside `app.app_context()`, so the database is created and the demo user is inserted on first run.

## Dependencies

`requirements.txt`: `flask==3.1.3`, `werkzeug==3.1.6`, `pytest==8.3.5`, `pytest-flask==1.3.0`. `pytest` is installed but no tests exist yet — the first person to add tests should drop them under `tests/` (no `tests/` directory exists yet).

## Database

- **File:** `expense_tracker.db` at the project root. Path is computed in `database/db.py` as `os.path.join(<project root>, "expense_tracker.db")` — do not hardcode the filename elsewhere; import `DB_PATH` from `database.db`.
- **Driver:** stdlib `sqlite3` only. **No SQLAlchemy / no ORM.**
- **Connection pattern** (`database/db.py:get_db`): opens a fresh connection per call, sets `row_factory = sqlite3.Row` (dict-like row access), and runs `PRAGMA foreign_keys = ON` on every open (SQLite's FK pragma is per-connection, not persisted).
- **Schema:**
  - `users(id, name, email UNIQUE, password_hash, created_at)` — `created_at` defaults to `datetime('now')`.
  - `expenses(id, user_id FK→users.id, amount REAL, category TEXT, date TEXT 'YYYY-MM-DD', description TEXT NULL, created_at)` — `amount` is `REAL`, not `INTEGER` (rupees with paise).
- **Categories** are a fixed 7-value tuple exported as `database.db.CATEGORIES`: `Food, Transport, Bills, Health, Entertainment, Shopping, Other`. Use this constant for form selects / validation — do not redefine the list inline.
- **`seed_db()` is idempotent**: short-circuits when `users` is non-empty, so do not add duplicate-seed logic at the call site.
- **Rules (from spec §11):** parameterised queries only — never use `%`/`f"…"` in SQL. Hash passwords with `werkzeug.security.generate_password_hash`. Enable FK pragma on every connection. Dates always `YYYY-MM-DD`.

## Code layout

```
app.py                          # Flask app + route stubs (one per future feature step)
database/
  __init__.py                   # empty package marker
  db.py                         # get_db, init_db, seed_db, CATEGORIES, DB_PATH
templates/                      # Jinja2: base, landing, login, register, terms, privacy
static/css/style.css, static/js/main.js
.claude/
  specs/NN-<step>.md            # step-by-step build spec — read the one for your step
  commands/                     # slash-command definitions (seed-user, seed-expense, create-spec)
  settings.local.json           # local permission allowlist
expense_tracker.db              # SQLite file, created on first run (gitignored implicitly by being untracked)
```

Routes in `app.py` are split into two groups: implemented ones (`/`, `/register`, `/login`, `/terms`, `/privacy`) that just render templates, and **placeholder** ones that return a "coming in Step N" string (`/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`). When implementing a step, replace the matching placeholder — do not invent new route paths unless the spec says so.

## Claude Code skills available in this repo

- `seed-user` — insert one dummy user (used during development, not by end users).
- `seed-expense` — bulk-insert realistic Indian-context expenses for a given user; reads `db.py` for schema and connection pattern, uses `get_db()` rather than hardcoding the DB path, and inserts in one transaction (rollback on any failure).
- `create-spec` — create the next `NN-<step>.md` spec file and feature branch.
- `init` — generate this `CLAUDE.md`.

## Permissions already allowlisted in `.claude/settings.local.json`

`python app.py`, `python -c "..."` smoke tests, `python _smoke_test.py`, `python` (bare), and the `seed-user` skill. Other Bash commands will prompt.
