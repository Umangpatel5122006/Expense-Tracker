# Spec: Add Expense

## Overview
This feature allows authenticated users to record new expenses. It provides a form to input the amount, category, date, and an optional description. This is a core functionality of Spendly, enabling users to populate their spending history for later analysis on the profile and analytics pages.

## Depends on
- 01-database-setup
- 03-login-and-logout

## Routes
- `GET /expenses/add` — Render the add expense form — logged-in
- `POST /expenses/add` — Validate and save the new expense — logged-in

## Database changes
No database changes.

## Templates
- **Create:** `templates/add_expense.html`
- **Modify:** `templates/base.html` (add link to "Add Expense" in navigation)

## Files to change
- `app.py` — Implement the `/expenses/add` route logic.
- `database/db.py` — (Optional) Add a helper function for inserting expenses if not done inline.

## Files to create
- `templates/add_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Do NOT create any standalone `.py` script files — run all Python inline via Bash heredoc only
- Validate that the amount is a positive number.
- Validate that the category is one of the allowed values from `database.db.CATEGORIES`.
- Ensure the date is in `YYYY-MM-DD` format.

## Definition of done
- [ ] Logged-out users are redirected to `/login` when visiting `/expenses/add`.
- [ ] The "Add Expense" form renders correctly and extends `base.html`.
- [ ] The category dropdown is populated using `database.db.CATEGORIES`.
- [ ] Valid expenses are successfully saved to the `expenses` table in the database.
- [ ] Invalid inputs (e.g., negative amount, invalid category, empty date) trigger an error message on the form.
- [ ] After a successful save, the user is redirected back to their `/profile` page.
