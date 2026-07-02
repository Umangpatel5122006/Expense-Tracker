# Spec: Registration

## Overview
Implement user registration for Spendly. The `/register` route currently renders a static form; this step wires the form up to the SQLite `users` table created in Step 1. When a user submits valid name/email/password, a new row is inserted (with the password hashed via `werkzeug.security.generate_password_hash`) and the user is automatically signed in via Flask session. This is the first half of authentication and is required before Login (Step 3) and every authenticated feature that follows.

## Depends on
- **Step 1 — Database setup** (complete): `users` table with `id, name, email UNIQUE, password_hash, created_at` must already exist, and `database.db.get_db()` must be importable.

## Routes
- `GET  /register` — render the registration form (name, email, password). On GET, the form is blank. — **public**
- `POST /register` — accept `name`, `email`, `password` from the form. Validate, hash the password, insert a new user, log them in, and redirect to the landing page (`/`). On validation failure, re-render the form with an error message. — **public**

## Database changes
No database changes. The `users` table created in Step 1 already supports registration: `id` autoincrement, `email` unique, `password_hash` not null, `created_at` defaulting to `datetime('now')`.

## Templates
- **Modify:** `templates/register.html` — already extends `base.html` and renders name/email/password fields with an `error` block. No structural change required; verify it still extends `base.html` and submits to `/register` via POST. The handler will be the source of the `error` context variable.
- **Modify:** `templates/base.html` — no change strictly required, but the existing nav links (`Sign in`, `Get started`) already point to `/login` and `/register` and work once the routes accept POST.

## Files to change
- `app.py` — convert the `register` view from a one-line `render_template` stub into a function that handles both GET and POST, performs validation, inserts into the `users` table, sets a session cookie identifying the new user, and redirects on success.
- `templates/register.html` — no structural edit needed, but verify the form posts to `/register` and the `error` block is preserved.

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug.security.generate_password_hash` is already a dependency (used in `database/db.py`).

## Rules for implementation
- **No SQLAlchemy or any ORM.** Use `sqlite3` from the standard library via `database.db.get_db()`.
- **Parameterised queries only.** Never use `%`/`f"…"`/`+` to build SQL — pass values as the second argument to `cursor.execute`.
- **Passwords must be hashed** with `werkzeug.security.generate_password_hash` before being written to `users.password_hash`. Never store plaintext, never log it.
- **Validate input on the server** even though the form uses `required` and `type="email"`:
  - `name`: stripped, must be non-empty and at most 100 characters.
  - `email`: stripped, lower-cased, must match a basic email shape (contains exactly one `@` with non-empty parts), must be at most 254 characters (RFC 5321 practical limit).
  - `password`: must be at least 8 characters.
  - On any failure, re-render `register.html` with an `error` string and preserve the entered `name` and `email` (not the password) so the user does not retype everything.
- **Duplicate email handling.** Catch `sqlite3.IntegrityError` raised by the `UNIQUE` constraint on `users.email` and re-render the form with a friendly error like `"An account with that email already exists."` — do not let a 500 escape.
- **Session.** Use Flask's `session` to mark the user as signed in. Store only the new user's `id` (e.g. `session["user_id"] = user_id`). `app.secret_key` must be set in `app.py` to a non-empty value; pick a deterministic-but-not-hardcoded-secret value via an env var, falling back to a dev default with a clear comment. (Plain `app.secret_key = "dev-key-change-me"` is acceptable for this step — Step 3 may revisit.)
- **Redirects.** On success, `return redirect(url_for("landing"))` (HTTP 302) — do not return the landing page directly.
- **Use CSS variables** — never hardcode hex values in any new template or CSS. (The register form already uses existing classes; no new colors are introduced.)
- **All templates extend `base.html`.** `register.html` already does; do not change that.
- **Do NOT create any standalone `.py` script files** for testing or seeding. Run all Python inline via `Bash` heredoc. Existing skills (`seed-user`) handle dev seeding.
- **Idempotency / safety.** Do not modify `seed_db()`. Do not change `DB_PATH` or `CATEGORIES`. Registration should not touch the demo user or sample expenses.

## Definition of done
- [ ] `GET /register` renders the form with empty fields and no `error`.
- [ ] `POST /register` with `name="Alice"`, `email="alice@example.com"`, `password="hunter2hunter2"` creates a new row in `users` and redirects (302) to `/`.
- [ ] The new row's `password_hash` is a `pbkdf2:`/`scrypt:` hash (length > 50), not the plaintext.
- [ ] After a successful registration, the Flask session contains the new user's `id`.
- [ ] `POST /register` with an already-registered email re-renders the form with error `"An account with that email already exists."` and returns HTTP 200 (not 500).
- [ ] `POST /register` with a password shorter than 8 characters re-renders the form with an error and returns HTTP 200.
- [ ] `POST /register` with an empty `name` re-renders the form with an error and returns HTTP 200.
- [ ] `POST /register` with an email missing `@` re-renders the form with an error and returns HTTP 200.
- [ ] After a failed POST, the previously entered `name` and `email` are pre-filled in the form; the password field is empty.
- [ ] `app.secret_key` is set in `app.py` (no `RuntimeError` from Flask when reading `session`).
- [ ] The app still starts cleanly with `python app.py` on port 5001 and the existing demo user (`demo@spendly.com` / `demo123`) can still be viewed in the database.
- [ ] No new files outside of `app.py` and `templates/register.html`. No new pip packages.
- [ ] No SQL string formatting — only `?` placeholders.
