# Spec: Login and Logout

## Overview
Complete the first half of authentication for Spendly by turning the `/login` route stub into a real view that authenticates existing users against the `users` table, and by replacing the `/logout` placeholder with a route that clears the session. After this step, returning users can sign in with their email and password, and any signed-in user can sign out from any page. Step 4 (Profile) and every subsequent authenticated feature depend on this — they will read `session["user_id"]` to identify the current user.

## Depends on
- **Step 1 — Database setup** (complete): `users` table with `id, email UNIQUE, password_hash` and `database.db.get_db()` must be importable.
- **Step 2 — Registration** (complete): `app.secret_key` must be set in `app.py` and the registration route must populate `session["user_id"]` on success. Login is the matching read-side.

## Routes
- `POST /login` — accept `email` and `password` from the form. Look up the user by email, verify the password against the stored hash with `werkzeug.security.check_password_hash`, and on success set `session["user_id"]` and redirect to `/`. On any failure, re-render `login.html` with a generic error and the entered email (never the password). — **public**
- `GET  /login` — render the login form (email, password). The form submits via POST. If the user is already signed in, redirect to `/` instead of rendering the form. — **public**
- `GET  /logout` — clear `session["user_id"]` and redirect to `/` (the landing page). Safe to call when no user is signed in. — **public**

## Database changes
No database changes. The `users` table created in Step 1 already supports login: `email` is UNIQUE (one row per email) and `password_hash` holds the `pbkdf2:`/`scrypt:` hash written during registration. No new columns or tables.

## Templates
- **Modify:** `templates/login.html` — already extends `base.html` and renders email/password fields with an `error` block. No structural change required; verify it still extends `base.html`, posts to `/login` via POST, and exposes an `error` context variable. The handler will be the source of the `error` and `email` context variables.
- **Modify:** `templates/base.html` — when the user is signed in, the nav should offer a working "Log out" link to `/logout` instead of (or in addition to) the "Sign in" link. When the user is not signed in, keep the existing "Sign in" / "Get started" links pointing at `/login` and `/register`. The login page itself may visually suppress the "Sign in" link.

## Files to change
- `app.py` — convert the `login` view from a one-line `render_template` stub into a function that handles both GET and POST, looks the user up by email, verifies the password, sets the session, and redirects on success. Replace the `/logout` placeholder with a real view that pops `session` (or `session.clear()`) and redirects to `/`. Also add a guard at the top of `/login` (and `/register`, for consistency) that redirects to `/` if `session["user_id"]` is already set, so a signed-in user who navigates to either auth form is bounced back to the landing page.
- `templates/login.html` — verify the form action is `"/login"`, the method is `POST`, and an `error` block is rendered when the handler sets one. Preserves the entered email after a failed POST.
- `templates/base.html` — adjust the nav so it shows "Log out" when `session.user_id` is set and "Sign in" / "Get started" otherwise. (The exact label/wording is up to the implementer; the requirement is that the two states differ.)

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug.security.check_password_hash` ships with the `werkzeug` package already in `requirements.txt` (it is the read-side companion to `generate_password_hash` used in Step 2).

## Rules for implementation
- **No SQLAlchemy or any ORM.** Use `sqlite3` from the standard library via `database.db.get_db()`.
- **Parameterised queries only.** Never use `%`/`f"…"`/`+` to build SQL — pass values as the second argument to `cursor.execute`. The email lookup must use a `?` placeholder.
- **Password verification.** Use `werkzeug.security.check_password_hash(stored_hash, submitted_password)`. Never compare hashes or passwords with `==`. Never log the submitted password.
- **Session.** On successful login, set `session["user_id"]` to the matching `users.id` (an integer). On logout, clear the session (`session.clear()` is fine) so `session.get("user_id")` returns `None`. `app.secret_key` is already set in `app.py` from Step 2 — do not change it.
- **Email handling.** Strip whitespace and lower-case the submitted email before the lookup, exactly as registration does on insert. The case must match the value in `users.email` (which is already stored lower-case by Step 2).
- **Generic error messages.** When the email is not found OR the password is wrong, return the same error: `"Invalid email or password."` Do not leak which one was wrong — attackers should not be able to enumerate registered emails via the login response.
- **Form re-rendering.** On failure, re-render `login.html` with `error` set to the generic message and the submitted `email` so the user does not retype it. Never pre-fill the password field.
- **Rate limiting / lockouts.** Out of scope for this step. A failed login simply re-renders the form. (Add a per-IP/per-account lockout in a later step if needed.)
- **Redirects.** On success, `return redirect(url_for("landing"))` (HTTP 302). On logout, `return redirect(url_for("landing"))` (HTTP 302) regardless of whether the user was actually signed in.
- **Method restriction for logout.** Use `GET /logout` (matches the placeholder and the nav link). If a CSRF concern arises in a later step, switch logout to POST; for now, GET is fine and consistent with the existing nav.
- **Use CSS variables** — never hardcode hex values in any new template or CSS. Reuse the existing form classes; no new colors are introduced.
- **All templates extend `base.html`.** `login.html` already does; do not change that. `base.html` changes are limited to the nav conditional.
- **Do NOT create any standalone `.py` script files** for testing or seeding. Run all Python inline via `Bash` heredoc. The existing `seed-user` skill remains the way to create dev users.
- **Idempotency / safety.** Do not modify `seed_db()`, `DB_PATH`, or `CATEGORIES`. Login must not insert rows. Logout must not touch the database.

## Definition of done
- [ ] `GET /login` renders the form with empty fields and no `error`.
- [ ] `GET /login` while signed in redirects (302) to `/` without rendering the form.
- [ ] `POST /login` while signed in redirects (302) to `/` without doing any DB lookup or form work.
- [ ] `GET /register` while signed in redirects (302) to `/` without rendering the form.
- [ ] `POST /register` while signed in redirects (302) to `/` without doing any DB lookup or form work.
- [ ] `POST /login` with the seeded demo user's email (`demo@spendly.com`) and password (`demo123`) sets `session["user_id"]` to the demo user's `id` and returns a 302 redirect to `/`.
- [ ] `POST /login` with a registered email but the **wrong** password re-renders the form with error `"Invalid email or password."`, returns HTTP 200, and does **not** set `session["user_id"]`.
- [ ] `POST /login` with an email that is not in the `users` table re-renders the form with the same `"Invalid email or password."` error and returns HTTP 200 — the response body is identical to the wrong-password case.
- [ ] `POST /login` with an empty `email` or empty `password` re-renders the form with an error and returns HTTP 200; no DB lookup is performed for an empty email.
- [ ] After a failed POST, the entered `email` is pre-filled in the form; the password field is empty.
- [ ] `GET /logout` clears `session["user_id"]` (subsequent `session.get("user_id")` is `None`) and returns a 302 redirect to `/`. Calling `/logout` again when no user is signed in is safe (still a 302 to `/`, no error).
- [ ] After login, `base.html` renders a "Log out" link to `/logout` instead of the "Sign in" / "Get started" links. After logout (or before login), the original "Sign in" / "Get started" links reappear.
- [ ] The app still starts cleanly with `python app.py` on port 5001 and the seeded demo user (`demo@spendly.com` / `demo123`) can log in successfully.
- [ ] No new files outside of `app.py`, `templates/login.html`, and `templates/base.html`. No new pip packages.
- [ ] No standalone `.py` script files created anywhere in the project — all one-off Python runs executed inline via Bash heredoc only.
- [ ] No SQL string formatting — only `?` placeholders. Password comparison goes through `check_password_hash`, never `==`.

## Technical Debt

### GET /logout CSRF Risk
`GET /logout` is acceptable for this iteration but carries a known 
CSRF vulnerability. Any external site can force-logout a signed-in 
user with a single invisible tag:

```html
<img src="https://spendly.com/logout">
```

The browser follows the GET request automatically — no user click needed.

**Industry standard fix (future step):**
- Change `/logout` to `POST` only
- Generate a CSRF token per session
- Embed token in the logout form/button
- Verify token on the server before clearing session

**Track as:** low severity for a personal expense tracker,
high severity for any multi-user or financial production app.

**Fix in:** Step 10 or whenever authentication hardening is addressed.