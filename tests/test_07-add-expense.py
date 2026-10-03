import os
import sys
import pytest
from datetime import datetime

# Ensure project root is in path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db
from database.db import init_db, CATEGORIES

@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """
    Fixture to provide a Flask test client with an isolated SQLite database.
    Follows the pattern established in test_backend_connection.py.
    """
    test_db = tmp_path / "test_app.db"
    # Redirect DB_PATH in database.db to use the temporary file
    monkeypatch.setattr(db, "DB_PATH", str(test_db))

    # Initialize schema
    init_db()

    # Import app after monkeypatching DB_PATH to ensure app.py uses the test DB
    import app as app_module
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        yield client

@pytest.fixture
def authenticated_client(app_client):
    """
    Fixture that provides a client logged in as the demo user.
    Relies on seed_db having been called (which happens in app.py's bootstrap).
    """
    # Since app.py calls seed_db() in its bootstrap, the demo user exists.
    # If seed_db is not called by app.py on import, we would call it here.
    # We'll explicitly seed just in case the app.py bootstrap is modified.
    from database.db import seed_db
    seed_db()

    app_client.post("/login", data={
        "email": "demo@spendly.com",
        "password": "demo123"
    })
    return app_client

# ------------------------------------------------------------------ #
# Auth Guards                                                         #
# ------------------------------------------------------------------ #

def test_add_expense_get_unauthenticated_redirects(app_client):
    """Verify that unauthenticated users are redirected to /login on GET /expenses/add."""
    response = app_client.get("/expenses/add", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"

def test_add_expense_post_unauthenticated_redirects(app_client):
    """Verify that unauthenticated users are redirected to /login on POST /expenses/add."""
    response = app_client.post("/expenses/add", data={"amount": "100"}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"

# ------------------------------------------------------------------ #
# Happy Path                                                          #
# ------------------------------------------------------------------ #

def test_add_expense_form_renders(authenticated_client):
    """Verify GET /expenses/add renders correctly and contains all categories."""
    response = authenticated_client.get("/expenses/add")
    assert response.status_code == 200

    # Check that all categories from db.CATEGORIES are present in the HTML
    for category in CATEGORIES:
        assert category in response.get_data(as_text=True)

    # Verify form extends base.html (check for common base elements like nav or title)
    assert "Spendly" in response.get_data(as_text=True)

def test_add_expense_success(authenticated_client):
    """Verify valid expense is saved to DB and redirects to /profile."""
    payload = {
        "amount": "125.50",
        "category": "Food",
        "date": "2026-10-04",
        "description": "Dinner at the bistro"
    }
    response = authenticated_client.post("/expenses/add", data=payload, follow_redirects=False)

    # Verify redirect to profile
    assert response.status_code == 302
    assert response.headers["Location"] == "/profile"

    # Verify DB state
    from database.db import get_db
    conn = get_db()
    row = conn.execute(
        "SELECT amount, category, date, description FROM expenses WHERE description = ?",
        ("Dinner at the bistro",)
    ).fetchone()
    conn.close()

    assert row is not None
    assert row["amount"] == 125.50
    assert row["category"] == "Food"
    assert row["date"] == "2026-10-04"

# ------------------------------------------------------------------ #
# Validation Errors                                                   #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("invalid_amount, error_msg", [
    ("-10.00", "Please enter a valid positive amount."),
    ("0", "Please enter a valid positive amount."),
    ("abc", "Please enter a valid positive amount."),
    ("", "Please enter a valid positive amount."),
])
def test_add_expense_invalid_amount(authenticated_client, invalid_amount, error_msg):
    """Verify that negative, zero, or non-numeric amounts trigger an error."""
    payload = {
        "amount": invalid_amount,
        "category": "Food",
        "date": "2026-10-04",
        "description": "Test"
    }
    response = authenticated_client.post("/expenses/add", data=payload)
    assert response.status_code == 200
    assert error_msg in response.get_data(as_text=True)

def test_add_expense_invalid_category(authenticated_client):
    """Verify that a category not in CATEGORIES triggers an error."""
    payload = {
        "amount": "100",
        "category": "Luxury",  # Not in CATEGORIES
        "date": "2026-10-04",
        "description": "Test"
    }
    response = authenticated_client.post("/expenses/add", data=payload)
    assert response.status_code == 200
    assert "Please select a valid category." in response.get_data(as_text=True)

@pytest.mark.parametrize("invalid_date, error_msg", [
    ("", "Date is required."),
    ("2026-13-01", "Please enter a valid date in YYYY-MM-DD format."),
    ("04-10-2026", "Please enter a valid date in YYYY-MM-DD format."),
    ("not-a-date", "Please enter a valid date in YYYY-MM-DD format."),
])
def test_add_expense_invalid_date(authenticated_client, invalid_date, error_msg):
    """Verify that missing or malformed dates trigger an error."""
    payload = {
        "amount": "100",
        "category": "Food",
        "date": invalid_date,
        "description": "Test"
    }
    response = authenticated_client.post("/expenses/add", data=payload)
    assert response.status_code == 200
    assert error_msg in response.get_data(as_text=True)

# ------------------------------------------------------------------ #
# Edge Cases                                                          #
# ------------------------------------------------------------------ #

def test_add_expense_optional_description_empty(authenticated_client):
    """Verify that an expense can be saved without a description."""
    payload = {
        "amount": "50.00",
        "category": "Transport",
        "date": "2026-10-04",
        "description": ""
    }
    response = authenticated_client.post("/expenses/add", data=payload, follow_redirects=False)
    assert response.status_code == 302

    from database.db import get_db
    conn = get_db()
    row = conn.execute(
        "SELECT description FROM expenses WHERE amount = ? AND category = ?",
        (50.00, "Transport")
    ).fetchone()
    conn.close()

    assert row is not None
    assert row["description"] is None or row["description"] == ""

def test_add_expense_long_description(authenticated_client):
    """Verify that extremely long descriptions are handled correctly."""
    long_desc = "A" * 1000
    payload = {
        "amount": "20.00",
        "category": "Other",
        "date": "2026-10-04",
        "description": long_desc
    }
    response = authenticated_client.post("/expenses/add", data=payload, follow_redirects=False)
    assert response.status_code == 302

    from database.db import get_db
    conn = get_db()
    row = conn.execute(
        "SELECT description FROM expenses WHERE description = ?",
        (long_desc,)
    ).fetchone()
    conn.close()

    assert row is not None
    assert row["description"] == long_desc
