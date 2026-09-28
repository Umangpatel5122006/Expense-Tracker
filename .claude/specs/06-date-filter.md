# Spec: Date Filter for Profile Page

## Overview
Add a date-range filter to the `/profile` page so the signed-in user can narrow the **Recent expenses** list, the **Total spent** and **Total expenses** tiles, and the **Spending by category** / **Distribution** sections down to a window they pick. The filter is a from/to date pair passed as query-string parameters on `GET /profile`; the route threads the same window through every query helper so every section on the page reflects the same range. Empty/blank inputs mean "no bound on that side" — `from` alone restricts the start, `to` alone restricts the end, neither means "all time" (the current behaviour). The filter UI is rendered above the Recent expenses card and re-applied on form submit; no JavaScript is required.

This step extends Step 5 (recent expenses) by adding the most common slice a user actually wants — "what did I spend this month / last week / in July?" — without yet introducing a full `/expenses` listing page (that's a later step).

## Depends on
- **Step 1 — Database setup** (complete): `expenses.date TEXT` (`YYYY-MM-DD`) and `get_db()`.
- **Step 2 — Registration** (complete): so a signed-in user exists.
- **Step 3 — Login and Logout** (complete): `session["user_id"]` is the user identity.
- **Step 4 — Profile page** (complete): `/profile` route + `profile.html` exist.
- **Step 5 — Recent expenses on profile** (complete): the query helpers in `database/queries.py` and the four profile sections being filtered.

## Routes

Modify:

- `GET /profile` — accept optional `from` and `to` query-string parameters (`YYYY-MM-DD`). Validate, apply to every query helper used by the page, and render `profile.html` with the active range and the filtered results. — **logged-in**

No new routes.

## Database changes
No database changes. The filter is purely a runtime `WHERE` clause against the existing `expenses` table. `expenses.date` is already `TEXT NOT NULL` in `YYYY-MM-DD` form, so lexicographic comparison is correct for `>=` / `<=`.

## Templates

Modify:

- `templates/profile.html`
  - Above the **Recent expenses** section, add a small filter form: two `<input type="date">` fields (one for `from`, one for `to`), an **Apply** submit button, and a **Clear** link (a plain `<a>` to `/profile` with no query string). Inputs are pre-filled with the active `from` / `to` (empty if not set) so the user can see and edit the current range.
  - All four dynamic sections — Activity stat tiles, Spending by category, Distribution, Recent expenses — must reflect the filter. The Activity stat-tile meta label changes from "all time" to a human-readable range (e.g. `1 July 2026 – 23 July 2026`, `since 1 July 2026`, `until 23 July 2026`, or `all time` when both are unset).
  - Recent expenses section title changes from `Last 10` to `Last 10 in range` when a filter is active; back to `Last 10` when no filter is active.
  - When the filter excludes every expense, the existing empty-state copy in the Recent expenses card is shown — same wording as today, no special "no results" copy.
  - No structural HTML changes elsewhere; keep extending `base.html`.

## Files to change

- `app.py` — `/profile` view:
  1. Read `request.args.get("from")` and `request.args.get("to")` (both `str | None`).
  2. Validate each against `YYYY-MM-DD` (parse with `datetime.strptime`; on failure, ignore the bad value and treat as `None`). Do not 400 — silently drop the bad value so a malformed link in an email can't break the page.
  3. If both are present and `from > to`, swap them (don't reject the request).
  4. Pass the validated `date_from` and `date_to` into `get_summary_stats`, `get_recent_transactions`, and `get_category_breakdown`.
  5. Pass the active range into the template (e.g. `date_from`, `date_to`, plus a pre-formatted `range_label` string the template can use in the stat-tile meta).

- `database/queries.py` — extend the three read helpers:
  - `get_summary_stats(conn, user_id, date_from=None, date_to=None)`
  - `get_recent_transactions(conn, user_id, limit=10, date_from=None, date_to=None)`
  - `get_category_breakdown(conn, user_id, date_from=None, date_to=None)`
  - All three helpers must accept the new optional kwargs and add `AND date >= ?` / `AND date <= ?` to their `WHERE` clauses when those kwargs are not `None`. Only one parameterised clause per bound is appended; never build SQL by string concatenation of user input.

- `templates/profile.html` — see Templates above.

## Files to create
None.

## New dependencies
No new dependencies. Date parsing uses the stdlib `datetime` module. The `<input type="date">` element is plain HTML5 — no JS, no library.

## Rules for implementation
- **No SQLAlchemy or any ORM.** Raw `sqlite3` only via `database.db.get_db()`.
- **Parameterised queries only.** The new `WHERE` clauses must use `?` placeholders. Never interpolate `date_from` / `date_to` into the SQL string.
- **Validation, not rejection.** A bad `from` or `to` value (`not YYYY-MM-DD`) is dropped silently. The page still renders with the rest of the filter applied. This keeps the route robust to hand-edited URLs.
- **Inclusive bounds.** `date >= date_from` and `date <= date_to`. Both ends inclusive. Document this in the docstring of each helper.
- **Optional kwargs.** The new `date_from` / `date_to` parameters must be keyword-only or default to `None` so existing callers (and existing tests) keep working unchanged when they don't pass them.
- **Connection ownership unchanged.** Helpers still receive an open connection and must not call `get_db()` or `conn.close()`. The route still owns the single `try: ... finally: conn.close()` block.
- **Auth gate unchanged.** No `user_id` in session → redirect to `/login`, no DB work, no filter applied.
- **No new tables, no new columns, no migrations.** Purely a runtime `WHERE` change.
- **Use CSS variables — never hardcode hex values.** Reuse existing form/card classes from `static/css/style.css`; do not introduce new colors. The new date inputs can reuse the existing form input styling.
- **All templates extend `base.html`.** No new template files.
- **Do NOT create any standalone `.py` script files** for testing or seeding. Run all Python inline via `Bash` heredoc only.
- **Idempotency / safety.** Do not modify `seed_db()`, `DB_PATH`, or `CATEGORIES`. The profile view issues `SELECT`s only.

## Definition of done
- [ ] `GET /profile?from=2026-07-10&to=2026-07-23` (signed in as the demo user) returns HTTP 200 and the four dynamic sections show only expenses with `date` in `2026-07-10..2026-07-23` (inclusive).
- [ ] `GET /profile?from=2026-07-10` restricts to expenses on/after `2026-07-10`; `GET /profile?to=2026-07-05` restricts to expenses on/before `2026-07-05`.
- [ ] `GET /profile` with no query string behaves exactly as today: full "all time" results, "all time" meta label, "Last 10" section title.
- [ ] `GET /profile?from=garbage` is treated as no filter (silently dropped) — page renders the same as `GET /profile` with no query string.
- [ ] `GET /profile?from=2026-07-23&to=2026-07-01` swaps the bounds internally; the rendered range label reflects the swapped order (`2026-07-01–2026-07-23`) and results are unchanged from passing them in correct order.
- [ ] For the demo user's seeded data, the `Total spent`, `Total expenses`, and `Top category` tiles all change in response to a filter that excludes some expenses (e.g. `from=2026-07-15` removes the 18-day-old and 25-day-old rows and reduces the totals accordingly).
- [ ] The Spending by category section and the Distribution section both show only categories with non-zero spend in the active range; categories with zero in-range spend still appear in Spending by category with `0%` and `₹0.00` (matching Step 5 behaviour for empty users).
- [ ] Category percentages still sum to **exactly 100** for any non-empty filtered range (the same "largest absorbs the remainder" rule from Step 5 still holds inside the helper).
- [ ] Recent expenses list is capped at the most recent 10 rows **within the filtered range** (newest first), not "10 newest overall that happen to fall in the range" — i.e. the `LIMIT` is applied after the `WHERE`, not before.
- [ ] When a filter excludes every expense: Activity tiles show `0` / `₹0.00` / `—`; Recent expenses shows the existing empty-state copy; Spending by category shows all 7 categories at `0%` / `₹0.00`; the Distribution section is hidden (same `{% if has_spend %}` gate as today).
- [ ] The filter form on `profile.html` has `from` and `to` `<input type="date">` fields pre-filled with the active range, an Apply button, and a Clear link to `/profile`. Submitting the form (GET) re-renders the page with the new range. No JavaScript is required.
- [ ] The Activity stat-tile meta label changes correctly: `all time` (no filter), `since <date>` (only `from`), `until <date>` (only `to`), `<from> – <to>` (both), with dates rendered in the same `9 July 2026` format used for `member_since`.
- [ ] `GET /profile` while **not** signed in still redirects to `/login` regardless of query string — no DB work, no filter applied.
- [ ] Existing Step 5 unit and route tests still pass unchanged (the new `date_from` / `date_to` kwargs are optional and default to `None`, so old call sites are not broken).
- [ ] New tests cover: in-range inclusive bounds, `from`-only, `to`-only, malformed `from`/`to` is dropped, swapped bounds, empty filtered result, Recent-expenses `LIMIT` applied after `WHERE`, percentage sums to 100 inside a filtered range, unauthenticated request with query string still redirects.
- [ ] The app still starts cleanly with `python app.py` on port 5001.
- [ ] No new files outside of `app.py`, `database/queries.py`, and `templates/profile.html`. No new pip packages. No standalone `.py` script files.
- [ ] No SQL string formatting — only `?` placeholders. The profile view performs `SELECT` only.
