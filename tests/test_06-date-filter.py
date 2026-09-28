import os
import sys
import pytest
import re
from datetime import datetime

# Ensure project root is in sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db
from database.db import init_db, get_db
from app import app, parse_date_range

@pytest.fixture
def unit_conn(tmp_path, monkeypatch):
    """Provides a fresh SQLite connection for unit tests, isolated from production DB."""
    test_db = tmp_path / "unit.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db))
    init_db()
    conn = get_db()
    yield conn
    conn.close()

@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """Provides a Flask test client with an isolated database."""
    test_db = tmp_path / "app.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db))
    init_db()

    # Import app inside fixture to ensure it uses the patched DB_PATH
    import app as app_module
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client

# --------------------------------------------------------------------- #
# Unit Tests: parse_date_range                                            #
# --------------------------------------------------------------------- #

@pytest.mark.parametrize("from_in, to_in, expected", [
    ("2026-07-01", "2026-07-10", ("2026-07-01", "2026-07-10")),  # Happy path
    ("2026-7-1", "2026-7-10", ("2026-07-01", "2026-07-10")),    # Normalization
    (None, "2026-07-10", (None, "2026-07-10")),                # From-only (None)
    ("", "2026-07-10", (None, "2026-07-10")),                  # From-only (Empty)
    ("  ", "2026-07-10", (None, "2026-07-10")),                # From-only (Whitespace)
    ("2026-07-01", None, ("2026-07-01", None)),                # To-only (None)
    ("2026-07-01", "garbage", ("2026-07-01", None)),           # One bad, one good
    ("garbage", "garbage", (None, None)),                      # Both bad
    ("2026-07-20", "2026-07-10", ("2026-07-10", "2026-07-20")), # Swapped bounds
    (None, None, (None, None)),                                # Both None
])
def test_parse_date_range(from_in, to_in, expected):
    """Verify date range parsing, normalization, and bound swapping per spec §40-44."""
    assert parse_date_range(from_in, to_in) == expected

# --------------------------------------------------------------------- #
# Integration Tests: /profile filter                                      #
# --------------------------------------------------------------------- #

def setup_test_user(client):
    """Helper to register and log in a test user."""
    client.post("/register", data={"name": "Test User", "email": "test@example.com", "password": "password123"})
    # Since registration logs in automatically in current implementation:
    return 1 # user_id is typically 1 in a fresh DB

def setup_test_expenses(conn, user_id):
    """Insert a controlled set of expenses for deterministic filtering."""
    expenses = [
        # Date, Amount, Category, Description
        ("2026-07-01", 100.0, "Food", "Meal 1"),
        ("2026-07-05", 200.0, "Transport", "Cab 1"),
        ("2026-07-10", 300.0, "Food", "Meal 2"),
        ("2026-07-15", 400.0, "Bills", "Internet"),
        ("2026-07-20", 500.0, "Entertainment", "Movie"),
        ("2026-07-25", 600.0, "Shopping", "Clothes"),
    ]
    for date, amt, cat, desc in expenses:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amt, cat, date, desc)
        )
    conn.commit()

def test_profile_auth_guard(app_client):
    """Verify unauthenticated requests to /profile redirect to /login regardless of query string."""
    # No query string
    resp = app_client.get("/profile")
    assert resp.status_code == 302
    assert resp.location.endswith("/login")

    # With query string
    resp = app_client.get("/profile?from=2026-07-01&to=2026-07-10")
    assert resp.status_code == 302
    assert resp.location.endswith("/login")

def test_profile_filter_happy_paths(app_client, unit_conn):
    """Verify inclusive bounds, from-only, to-only, and single-day ranges."""
    # Setup user and data
    app_client.post("/register", data={"name": "Filter User", "email": "filter@example.com", "password": "password123"})
    user_id = 1
    setup_test_expenses(unit_conn, user_id)

    # 1. Inclusive bounds: July 5 to July 15 (Expected: 200 + 300 + 400 = 900)
    resp = app_client.get("/profile?from=2026-07-05&to=2026-07-15")
    assert b"900" in resp.data # Total spent
    assert b"3" in resp.data   # Transaction count (Cab 1, Meal 2, Internet)

    # 2. From-only: since July 15 (Expected: 400 + 500 + 600 = 1500)
    resp = app_client.get("/profile?from=2026-07-15")
    assert b"1,500" in resp.data or b"1500" in resp.data
    assert b"3" in resp.data

    # 3. To-only: until July 5 (Expected: 100 + 200 = 300)
    resp = app_client.get("/profile?to=2026-07-05")
    assert b"300" in resp.data
    assert b"2" in resp.data

    # 4. Single day: July 10 (Expected: 300)
    resp = app_client.get("/profile?from=2026-07-10&to=2026-07-10")
    assert b"300" in resp.data
    assert b"1" in resp.data

def test_profile_filter_robustness(app_client, unit_conn):
    """Verify malformed dates, non-padded dates, and swapped bounds."""
    app_client.post("/register", data={"name": "Robust User", "email": "robust@example.com", "password": "password123"})
    user_id = 1
    setup_test_expenses(unit_conn, user_id)

    # 1. Non-padded date: 2026-7-1 -> 2026-07-01
    resp = app_client.get("/profile?from=2026-7-1&to=2026-7-1")
    assert b"100" in resp.data

    # 2. Swapped bounds: from=20th, to=1st -> should behave as 1st to 20th
    resp = app_client.get("/profile?from=2026-07-20&to=2026-07-01")
    # Total for 1-20 is 100+200+300+400+500 = 1500
    assert b"1,500" in resp.data or b"1500" in resp.data

    # 3. Malformed date dropped: from=garbage, to=2026-07-05 (Expected: until July 5 = 300)
    resp = app_client.get("/profile?from=garbage&to=2026-07-05")
    assert b"300" in resp.data

def test_profile_filter_empty_results(app_client, unit_conn):
    """Verify stats and UI when filter excludes all expenses."""
    app_client.post("/register", data={"name": "Empty User", "email": "empty@example.com", "password": "password123"})
    user_id = 1
    setup_test_expenses(unit_conn, user_id)

    # Range where no expenses exist (e.g., 2025)
    resp = app_client.get("/profile?from=2025-01-01&to=2025-01-31")
    assert "₹0.00".encode("utf-8") in resp.data
    assert b"0" in resp.data
    assert "—".encode("utf-8") in resp.data # top_category
    # Distribution should be hidden (has_spend is False)
    assert b"Distribution" not in resp.data

def test_profile_recent_expenses_limit(app_client, unit_conn):
    """Verify LIMIT 10 is applied after the date filter."""
    app_client.post("/register", data={"name": "Limit User", "email": "limit@example.com", "password": "password123"})
    user_id = 1

    # Insert 15 expenses in range
    for i in range(15):
        unit_conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, 10.0, "Food", "2026-07-01", f"Expense {i}")
        )
    unit_conn.commit()

    resp = app_client.get("/profile?from=2026-07-01&to=2026-07-01")
    # Count number of table rows in the recent expenses section
    assert resp.data.count(b"Expense") == 10

def test_profile_category_percentages_sum(app_client, unit_conn):
    """Verify category percentages sum to exactly 100 inside a filtered range."""
    app_client.post("/register", data={"name": "Pct User", "email": "pct@example.com", "password": "password123"})
    user_id = 1

    # Create a distribution that might cause rounding issues
    # Total = 1000. 33.3% x 3 = 99.9%
    unit_conn.execute("INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)", (user_id, 333.33, "Food", "2026-07-01"))
    unit_conn.execute("INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)", (user_id, 333.33, "Transport", "2026-07-01"))
    unit_conn.execute("INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)", (user_id, 333.34, "Bills", "2026-07-01"))
    unit_conn.commit()

    resp = app_client.get("/profile?from=2026-07-01&to=2026-07-01")

    # Extract percentages from the response
    # We search specifically in the 'Spending by category' section's rows
    # but since the template also repeats them in the 'Distribution' section,
    # we just need to ensure we only count one set.
    # a better way is to find the first occurrence of the breakdown.

    html = resp.data.decode()
    # Split by sections to isolate 'Spending by category'
    parts = html.split('Spending by category')
    if len(parts) < 2:
        pytest.fail("Spending by category section not found")

    category_section = parts[1].split('Distribution')[0]
    pcts = re.findall(r"(\d+)%", category_section)
    sum_pcts = sum(int(p) for p in pcts)
    assert sum_pcts == 100
