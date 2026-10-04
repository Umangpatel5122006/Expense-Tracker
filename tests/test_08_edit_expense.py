import os
import sys
import pytest
from database import db
from database.db import init_db, CATEGORIES

# Ensure project root is in path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """
    Fixture to provide a Flask test client with an isolated SQLite database.
    """
    test_db = tmp_path / "test_edit.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db))

    # Initialize schema
    init_db()

    import app as app_module
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        yield client

@pytest.fixture
def auth_client(app_client):
    """
    Fixture to provide a logged-in client.
    Uses the register route to create a user for the session.
    """
    app_client.post("/register", data={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123"
    })
    return app_client

@pytest.fixture
def seeded_expense(auth_client):
    """
    Creates a sample expense for the logged-in user and returns its ID.
    """
    from database.db import get_db
    conn = get_db()
    # Get the current user from session via the client's session is tricky,
    # so we query the DB for the user we just registered.
    user = conn.execute("SELECT id FROM users WHERE email = ?", ("test@example.com",)).fetchone()
    user_id = user["id"]

    cursor = conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, 100.0, "Food", "2026-10-01", "Initial Expense")
    )
    expense_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return expense_id

# ------------------------------------------------------------------ #
# Auth Guard Tests                                                    #
# ------------------------------------------------------------------ #

def test_edit_get_unauthenticated_redirects(app_client):
    """Spec: Unauthenticated GET requests MUST redirect to /login."""
    response = app_client.get("/expenses/1/edit")
    assert response.status_code == 302
    assert response.location.endswith("/login")

def test_edit_post_unauthenticated_redirects(app_client):
    """Spec: Unauthenticated POST requests MUST redirect to /login."""
    response = app_client.post("/expenses/1/edit", data={})
    assert response.status_code == 302
    assert response.location.endswith("/login")

# ------------------------------------------------------------------ #
# Ownership & Existence Tests                                         #
# ------------------------------------------------------------------ #

def test_edit_get_nonexistent_id_404(auth_client):
    """Spec: Accessing a nonexistent ID returns a 404."""
    response = auth_client.get("/expenses/9999/edit")
    assert response.status_code == 404

def test_edit_get_other_user_expense_404(auth_client, tmp_path, monkeypatch):
    """Spec: Accessing an expense ID belonging to another user returns a 404."""
    # Create a second user and an expense
    from database.db import get_db
    conn = get_db()
    conn.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                 ("Other", "other@ex.com", "hash"))
    other_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    expense_id = conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (other_id, 50.0, "Bills", "2026-10-01", "Other's Expense")
    ).lastrowid
    conn.commit()
    conn.close()

    response = auth_client.get(f"/expenses/{expense_id}/edit")
    assert response.status_code == 404

def test_edit_post_other_user_expense_404(auth_client, tmp_path, monkeypatch):
    """Spec: POST to an expense ID belonging to another user returns a 404."""
    from database.db import get_db
    conn = get_db()
    conn.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                 ("Other", "other@ex.com", "hash"))
    other_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    expense_id = conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (other_id, 50.0, "Bills", "2026-10-01", "Other's Expense")
    ).lastrowid
    conn.commit()
    conn.close()

    response = auth_client.post(f"/expenses/{expense_id}/edit", data={
        "amount": "60.0",
        "category": "Bills",
        "date": "2026-10-01",
        "description": "Hacked"
    })
    assert response.status_code == 404

# ------------------------------------------------------------------ #
# Pre-fill Tests                                                      #
# ------------------------------------------------------------------ #

def test_edit_get_prefills_form(auth_client, seeded_expense):
    """Spec: The edit form correctly pre-fills amount, category, date, and description."""
    response = auth_client.get(f"/expenses/{seeded_expense}/edit")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Check for pre-filled values in the HTML (usually in value attributes)
    assert 'value="100.0"' in html
    assert 'value="2026-10-01"' in html
    assert 'value="Initial Expense"' in html
    # Category should be selected
    assert f'selected' in html # Simplified; usually check <option value="Food" selected>

# ------------------------------------------------------------------ #
# Valid Update Tests                                                  #
# ------------------------------------------------------------------ #

def test_edit_post_valid_update(auth_client, seeded_expense):
    """Spec: Submitting valid data updates the database and redirects to the profile page."""
    update_data = {
        "amount": "150.75",
        "category": "Transport",
        "date": "2026-10-05",
        "description": "Updated Description"
    }
    response = auth_client.post(f"/expenses/{seeded_expense}/edit", data=update_data)

    # Verify redirect
    assert response.status_code == 302
    assert response.location.endswith("/profile")

    # Verify DB change
    from database.db import get_db
    conn = get_db()
    row = conn.execute("SELECT amount, category, date, description FROM expenses WHERE id = ?", (seeded_expense,)).fetchone()
    conn.close()

    assert row["amount"] == 150.75
    assert row["category"] == "Transport"
    assert row["date"] == "2026-10-05"
    assert row["description"] == "Updated Description"

def test_edit_post_update_description_to_empty(auth_client, seeded_expense):
    """Spec: Updating a description to be empty saves as None/empty string."""
    update_data = {
        "amount": "100.0",
        "category": "Food",
        "date": "2026-10-01",
        "description": "" # Empty description
    }
    auth_client.post(f"/expenses/{seeded_expense}/edit", data=update_data)

    from database.db import get_db
    conn = get_db()
    row = conn.execute("SELECT description FROM expenses WHERE id = ?", (seeded_expense,)).fetchone()
    conn.close()

    # Depending on implementation, could be None or "". Spec says "None/empty string".
    assert row["description"] in (None, "")

# ------------------------------------------------------------------ #
# Validation Tests                                                    #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("amount, category, date, description, expected_error", [
    ("-10", "Food", "2026-10-01", "Desc", "Please enter a valid positive amount."),
    ("0", "Food", "2026-10-01", "Desc", "Please enter a valid positive amount."),
    ("abc", "Food", "2026-10-01", "Desc", "Please enter a valid positive amount."),
    ("100", "InvalidCat", "2026-10-01", "Desc", "Please select a valid category."),
    ("100", "Food", "2026-13-01", "Desc", "Please enter a valid date in YYYY-MM-DD format."),
    ("100", "Food", "not-a-date", "Desc", "Please enter a valid date in YYYY-MM-DD format."),
    ("100", "Food", "", "Desc", "Date is required."),
    ("100", "Food", "2026-10-01", "a" * 501, "Description must be 500 characters or fewer."),
])
def test_edit_post_validation_errors(auth_client, seeded_expense, amount, category, date, description, expected_error):
    """Spec: Submitting negative amounts, bad dates, or invalid categories shows errors and preserves user input."""
    update_data = {
        "amount": amount,
        "category": category,
        "date": date,
        "description": description
    }
    response = auth_client.post(f"/expenses/{seeded_expense}/edit", data=update_data)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert expected_error in html

    # Verify user input preservation
    if amount: assert amount in html
    if category: assert category in html
    if date: assert date in html
    if description: assert description in html
