# Spec: Profile Page

## Overview
Replace the `/profile` placeholder with a real, read-only profile page that shows the signed-in user's account information (name, email, member-since date) and a small summary of their expense activity (total expenses, total amount spent, top category by spend). The page is the user's "home base" once they are signed in and the launching point for the expense-tracking features that follow in later steps. No editing happens on this step — name/email/password changes are out of scope here.

## Depends on
- **Step 1 — Database setup** (complete): `users` and `expenses` tables must exist, and `database.db.get_db()` must be importable.
- **Step 2 — Registration** (complete): `users` rows must be creatable so a signed-in user exists.
- **Step 3 — Login and Logout** (complete): `session["user_id"]` is the way to identify the current user; the logout link in the nav must work from this page too.

## Routes
- `GET /profile` — look up the current user (by `session["user_id"]`), load the user's account fields plus an expense activity summary, and render `profile.html`. If no user is signed in, redirect to `/login` (with a flash/note that the page requires sign-in — at minimum, the redirect itself). If the session's `user_id` does not match any row, clear the session and redirect to `/login`. — **logged-in**

No new routes. (No POST handler in this step — editing the profile is a later step.)

## Database changes
No database changes. The `users` and `expenses` tables from Step 1 already contain everything the profile page needs:
- `users.name`, `users.email`, `users.created_at`
- `expenses.user_id` (FK to `users.id`), `expenses.amount`, `expenses.category`

All profile-page data is computed at query time via `SELECT` / aggregation — no new columns, no new tables.

## Templates
- **Create:** `templates/profile.html` — extends `base.html`. Shows:
  - A header with the user's name and a small "Signed in as …" subtitle with the email.
  - An "Account" section with three labelled rows: **Name**, **Email**, **Member since** (the `created_at` value formatted as a readable date like `9 July 2026`).
  - An "Activity" section with three stat tiles: **Total expenses** (count), **Total spent** (sum of `amount`, formatted as ₹ with two decimals), **Top category** (the category with the highest total spend for this user; ties broken alphabetically; if the user has zero expenses, show `—`).
  - A "Coming soon" note that name/email editing and password changes are not available yet.
  - A call-to-action link/button to "View expenses" (it can currently be a non-link or a disabled link — no `/expenses` route exists yet; the spec only requires the visual placement of this CTA, not that it be wired up).
  - All copy is plain text, no JavaScript required to render the page.

- **Modify:** `templates/base.html` — when `session.user_id` is set, the nav should also show a "Profile" link to `/profile` (alongside the existing "Log out" link). When not signed in, the nav is unchanged from Step 3 (Sign in / Get started).

## Files to change
- `app.py` — replace the `/profile` placeholder with a real view that:
  1. Reads `session.get("user_id")`. If missing, redirect to `/login` (no DB work).
  2. Opens a connection via `database.db.get_db()`, looks up the user by `id` (parameterised), and fetches the activity aggregates from `expenses` filtered by `user_id` (parameterised).
  3. If the user row is `None` (deleted/old session id), clears the session and redirects to `/login`.
  4. Renders `profile.html` with the user row + activity summary as context.
- `templates/base.html` — add a "Profile" link in the signed-in branch of the nav (the same `{% if session.user_id %}` block that already shows "Log out").

## Files to create
- `templates/profile.html` — new template, extends `base.html`.

## New dependencies
No new dependencies. `sqlite3` (stdlib) and `werkzeug` are already in use. Date formatting can be done with the stdlib `datetime` module — no new pip packages.

## Rules for implementation
- **No SQLAlchemy or any ORM.** Use `sqlite3` from the standard library via `database.db.get_db()`.
- **Parameterised queries only.** Never use `%`/`f"…"`/`+` to build SQL — pass values as the second argument to `cursor.execute`. The user lookup and every aggregate must use `?` placeholders.
- **Authentication required.** `/profile` is a logged-in page. If `session.get("user_id")` is `None`, redirect to `/login` (do not render the template, do not query the DB). If the session id does not match any user, `session.clear()` and redirect to `/login`.
- **Do not modify `users` or `expenses` rows from this page.** Read-only. The profile view issues `SELECT`s only — no `UPDATE`, no `INSERT`, no `DELETE`.
- **Use the existing `database.db.CATEGORIES` constant** when validating / displaying the top category name (so the label matches the form values used by later expense steps). The top-category query is a `GROUP BY category` aggregation over the user's expenses; if the result is empty, render `—` rather than guessing.
- **Date formatting.** The `users.created_at` column is a `datetime('now')` string (e.g. `2026-07-09 14:32:11`). Format it for display as e.g. `9 July 2026` in the template or the handler — do not display the raw SQLite string. Do the formatting in Python (parse with `datetime.strptime`, format with `strftime` or `str`) so the template stays free of date-parsing logic.
- **Currency formatting.** Total spent is a sum of `REAL` values. Format it in the template as `₹<value with two decimals>` (e.g. `₹1,234.56`). Group thousands with a comma. Do not hardcode the rupee symbol in CSS — it is plain text in the template.
- **Use CSS variables** — never hardcode hex values in any new template or CSS. Reuse the existing form/card classes from `static/css/style.css`; do not introduce new colors.
- **All templates extend `base.html`.** `profile.html` must `{% extends "base.html" %}` and put its content inside a `{% block content %}` block.
- **Do NOT create any standalone `.py` script files** for testing or seeding. Run all Python inline via `Bash` heredoc. The existing `seed-user` and `seed-expense` skills remain the way to create dev users / data.
- **Idempotency / safety.** Do not modify `seed_db()`, `DB_PATH`, or `CATEGORIES`. The profile view must not insert, update, or delete rows.

## Definition of done
- [ ] `GET /profile` while **not** signed in redirects (302) to `/login` and does not query the database.
- [ ] `GET /profile` while signed in as the seeded demo user (`demo@spendly.com`) returns HTTP 200 and renders `profile.html` with the user's name (`Demo User`), email (`demo@spendly.com`), and a member-since date.
- [ ] The member-since date on the demo user's profile is formatted as a readable date (e.g. `9 July 2026`), not as the raw SQLite `YYYY-MM-DD HH:MM:SS` string.
- [ ] The Activity section shows three tiles: total expense count, total spent formatted as `₹<…>` with two decimals, and a top category. For the demo user's seeded data, the totals are non-zero and the top category is one of the seven `CATEGORIES` values.
- [ ] For a brand-new user with **zero** expenses, the profile page still renders successfully: the totals show `0` and `₹0.00`, and the top-category tile shows `—`.
- [ ] A session whose `user_id` does not match any `users.id` (e.g. user was deleted) clears the session and redirects (302) to `/login` — no 500 error.
- [ ] When signed in, the nav in `base.html` shows both a "Profile" link (to `/profile`) and a "Log out" link. When not signed in, the nav shows the original "Sign in" / "Get started" links.
- [ ] The app still starts cleanly with `python app.py` on port 5001; the demo user can log in, visit `/profile`, and see the page.
- [ ] No new files outside of `app.py`, `templates/profile.html`, and `templates/base.html`. No new pip packages.
- [ ] No standalone `.py` script files created anywhere in the project — all one-off Python runs executed inline via Bash heredoc only.
- [ ] No SQL string formatting — only `?` placeholders. The profile view performs `SELECT` only (no writes).
