# Spec: Edit Expense

## Overview
This feature allows logged-in users to modify the details of an existing expense they have recorded. Users can update the amount, category, date, and description of a specific transaction, ensuring their spending records remain accurate over time.

## Depends on
- 01-database-setup
- 03-login-and-logout
- 04-profile-page
- 05-recent-expenses-on-profile
- 07-add-expense

## Routes
- `GET /expenses/<int:id>/edit` — Display the edit form pre-filled with the expense's current data — logged-in
- `POST /expenses/<int:id>/edit` — Validate and save the updated expense data — logged-in

## Database changes
No database changes.

## Templates
- **Create:** `templates/edit_expense.html` — Reuses the same form layout and CSS classes as `add_expense.html`, with the heading "Edit expense" and the button "Save changes".
- **Modify:** `templates/profile.html` — Add an "Edit" link to each row in the Recent expenses list pointing to `/expenses/<id>/edit`.

## Files to change
- `app.py` — Implement the `edit_expense` route logic.
- `database/queries.py` — Add helper functions to retrieve and update expenses.
- `templates/profile.html` — Add links to the edit page.

## Files to create
- `templates/edit_expense.html`
- `tests/test_08_edit_expense.py`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Do NOT create any standalone `.py` script files — run all Python inline via Bash heredoc only
- **Auth Order:** Unauthenticated GET and POST requests MUST redirect to `/login` before any database work or ownership checks.
- **Ownership & Existence:** Both GET and POST requests must verify that the expense exists and belongs to the logged-in user. If either check fails, return a 404 response. The `update_expense` query must also include `AND user_id = ?` to prevent unauthorized edits if a route check is missed.
- **Editable Fields:** Only `amount`, `category`, `date`, and `description` can be changed. `user_id`, `id`, and `created_at` must never be taken from form data.
- **Validation:** Use the exact same validation logic as `07-add-expense` (shared in one helper function to avoid drift):
    - **Amount:** Numeric, greater than 0, at most 2 decimal places, no NaN/Inf.
    - **Date:** Strict `YYYY-MM-DD`. Re-serialise after parsing so `2026-7-5` becomes `2026-07-05`. Future dates are allowed.
    - **Category:** Must be present in `database.db.CATEGORIES`.
    - **Description:** Optional, max length 500 characters.
- **Error Response:** On validation failure, re-render the form with submitted values and a specific error message (status 200).
- **Database Helpers:**
    - `get_expense(conn, expense_id, user_id)`: returns a row or `None`.
    - `update_expense(conn, expense_id, user_id, *, amount, category, date, description)`: returns `True` if `rowcount > 0`, else `False`.
    - Helpers receive an open connection; the route owns the `try/finally` block and calls `conn.commit()`.
- **UI/UX:**
    - The category dropdown must have the current category pre-selected.
    - The date input must be pre-filled in `YYYY-MM-DD`.
    - Include a "Cancel" link on the edit form returning to `/profile`.
    - Success feedback: None requested (direct redirect to profile).

## Definition of done
- [ ] **Navigation:** Logged-in users can reach the edit page via "Edit" links on the profile page.
- [ ] **Pre-fill:** The edit form correctly pre-fills amount, category, date, and description.
- [ ] **Auth Guard:** Unauthenticated users are redirected to `/login` on both GET and POST.
- [ ] **Ownership Guard:** Accessing an expense ID belonging to another user or a nonexistent ID returns a 404 on both GET and POST.
- [ ] **Valid Update:** Submitting valid data updates the database and redirects to the profile page.
- [ ] **Invalid Data:** Submitting negative amounts, bad dates, or invalid categories shows errors and preserves user input.
- [ ] **Tests:** `tests/test_08_edit_expense.py` passes, covering:
    - GET pre-fill verification.
    - Valid POST updates and redirects.
    - Invalid input cases (amount $\le$ 0, non-numeric, bad date, bad category).
    - 404 for other users' expenses or nonexistent IDs on both GET and POST.
    - Unauthenticated redirects.
    - Regression: existing tests still pass.
- [ ] **General:** App starts on port 5001; `seed_db()`, `DB_PATH`, and `CATEGORIES` remain untouched.
