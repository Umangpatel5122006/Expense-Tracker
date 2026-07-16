# Spec: Backend Connection

## Overview
Step 5 replaces all hardcoded data in the `/profile` route with live queries
against the SQLite database. The profile page currently renders a static demo
user, fixed summary stats, a hand-typed transaction list, and a hardcoded
category breakdown.

This step wires those four sections to real database data so every logged-in
user sees their own information.

The implementation separates database logic into reusable query helpers while
using a single database connection per request for efficiency.

---

## Depends on

- Step 1: Database setup (`get_db()` and tables exist)
- Step 2: Registration
- Step 3: Login / Logout (`session["user_id"]`)
- Step 4: Static profile page

---

## Routes

No new routes.

Modify:

GET /profile

---

## Database changes

None.

Uses existing tables:

users

expenses

---

## Templates

Modify:

templates/profile.html

Replace all hardcoded values with Jinja variables.

Requirements:

- Display ₹ for every currency value.
- No structural HTML changes.
- Continue extending `base.html`.

---

## Files to change

app.py

templates/profile.html

---

## Files to create

database/queries.py

---

## Architecture

The `/profile` route opens **one SQLite connection** using `get_db()`.

That connection is passed into reusable query helper functions.

```
profile()
    ↓
conn = get_db()

user = get_user_by_id(conn, user_id)
stats = get_summary_stats(conn, user_id)
transactions = get_recent_transactions(conn, user_id)
categories = get_category_breakdown(conn, user_id)

render_template(...)
```

This avoids opening four database connections while still keeping database
logic separate from Flask routes.

---

## Query Helpers

database/queries.py

These functions contain **no Flask imports**.

```
get_user_by_id(conn, user_id)
```

Returns

```
{
    "name",
    "email",
    "member_since"
}
```

or

```
None
```

---

```
get_summary_stats(conn, user_id)
```

Returns

```
{
    "total_spent",
    "transaction_count",
    "top_category"
}
```

---

```
get_recent_transactions(conn, user_id, limit=10)
```

Returns

```
[
    {
        "date",
        "description",
        "category",
        "amount"
    }
]
```

Newest first.

---

```
get_category_breakdown(conn, user_id)
```

Returns

```
[
    {
        "name",
        "amount",
        "pct"
    }
]
```

Ordered by amount descending.

---

## Connection Management

Connection ownership belongs to the route.

```
conn = get_db()

try:
    ...
finally:
    conn.close()
```

Query helpers **must not** call `get_db()`.

Query helpers **must not** close the connection.

This ensures:

- One connection per request
- Easier testing
- Better performance
- Clear ownership

---

## Rules

- Raw sqlite3 only
- No SQLAlchemy
- Parameterised queries only (`?`)
- No f-string SQL
- Foreign keys already enabled in `get_db()`
- CSS variables only
- No inline styles
- All templates extend `base.html`
- Currency always displays as ₹
- `member_since` formatted as

```
January 2026
```

- Category percentages must total exactly **100**
    - Round each percentage
    - Adjust the largest category to absorb the rounding remainder
- Empty users return
    - total_spent = 0
    - transaction_count = 0
    - top_category = "—"
    - empty transaction list
    - empty category list

---

## Tests

### Unit Tests

tests/test_backend_connection.py

### get_user_by_id

- valid id
- invalid id

### get_summary_stats

- user with expenses
- user without expenses

### get_recent_transactions

- ordered newest first
- empty list

### get_category_breakdown

- ordered by amount
- percentages sum to exactly 100
- empty list

---

### Route Tests

GET /profile

Unauthenticated

- redirects to /login

Authenticated

- HTTP 200
- correct user name
- correct email
- contains ₹
- total spent = ₹346.24
- transaction count = 8
- top category = Bills
- newest-first transactions
- seven category rows

---

## Definition of Done

- Demo user information comes from the database.
- Total spent is ₹346.24.
- Transaction count is 8.
- Top category is Bills.
- Transactions display newest first.
- Category percentages total exactly 100.
- Every amount uses ₹.
- Brand-new users see:
    - ₹0.00 total spent
    - 0 transactions
    - empty recent transactions
    - empty category breakdown
    - no exceptions

---

## Design Principles

- Single Responsibility Principle
- One database connection per request
- Database logic isolated from Flask routes
- Reusable query helpers
- Easy unit testing
- No duplicated SQL
- Parameterised queries everywhere