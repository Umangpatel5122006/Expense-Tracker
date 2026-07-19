"""Unit and route tests for the /profile data path (Step 5).

These tests cover:
  - get_user_by_id
  - get_summary_stats
  - get_recent_transactions
  - get_category_breakdown
  - GET /profile (authenticated and unauthenticated)

A fresh SQLite file is created in pytest's tmp_path for every fixture
so tests never touch the real expense_tracker.db. The app fixture
re-points DB_PATH at the temp file before importing the app.

NOTE on seed totals: the spec at .claude/specs/05-recent-expenses-on-profile.md
claims the demo user has total_spent = Rs 346.24. The actual seed in
database/db.py sums to Rs 300.14. We assert against the real value
(300.14) and leave a comment so the divergence is discoverable.
"""

from __future__ import annotations

import os
import sys

import pytest

# Make the project importable when pytest is run from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db
from database.db import CATEGORIES, get_db, init_db, seed_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)


# --------------------------------------------------------------------- #
# Fixtures                                                               #
# --------------------------------------------------------------------- #

@pytest.fixture
def unit_conn(tmp_path, monkeypatch):
    """A fresh SQLite file in tmp_path, schema created, populated with
    a hand-rolled user + 3 expenses. Yields the open connection; closes
    after the test."""
    test_db = tmp_path / "unit.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db))
    init_db()
    c = get_db()
    c.execute(
        "INSERT INTO users (id, name, email, password_hash) "
        "VALUES (1, 'Test', 't@x.com', 'x')"
    )
    c.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (1, 60.0,  "Food",      "2026-06-30", "Lunch"),
            (1, 30.0,  "Transport", "2026-06-29", "Metro"),
            (1, 10.0,  "Bills",     "2026-06-28", "Recharge"),
        ],
    )
    c.commit()
    yield c
    c.close()


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """A Flask test client wired to a fresh DB seeded with the demo user."""
    test_db = tmp_path / "app.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db))
    init_db()
    seed_db()  # idempotent: writes demo user (id=1) + 8 expenses

    import app as app_module

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client


# --------------------------------------------------------------------- #
# get_user_by_id                                                         #
# --------------------------------------------------------------------- #

def test_get_user_by_id_valid(unit_conn):
    user = get_user_by_id(unit_conn, 1)
    assert user == {
        "name": "Test",
        "email": "t@x.com",
        "member_since": unit_conn.execute(
            "SELECT created_at FROM users WHERE id = 1"
        ).fetchone()["created_at"],
    }


def test_get_user_by_id_invalid(unit_conn):
    assert get_user_by_id(unit_conn, 999) is None


# --------------------------------------------------------------------- #
# get_summary_stats                                                      #
# --------------------------------------------------------------------- #

def test_get_summary_stats_with_expenses(unit_conn):
    stats = get_summary_stats(unit_conn, 1)
    assert stats["total_spent"] == 100.0
    assert stats["transaction_count"] == 3
    assert stats["top_category"] == "Food"   # highest single-category total = 60


def test_get_summary_stats_without_expenses(unit_conn):
    stats = get_summary_stats(unit_conn, 999)
    assert stats["total_spent"] == 0.0
    assert stats["transaction_count"] == 0
    assert stats["top_category"] == "—"


# --------------------------------------------------------------------- #
# get_recent_transactions                                                #
# --------------------------------------------------------------------- #

def test_get_recent_transactions_ordered_newest_first(unit_conn):
    tx = get_recent_transactions(unit_conn, 1)
    assert [t["date"] for t in tx] == ["2026-06-30", "2026-06-29", "2026-06-28"]
    # Tie-break by id DESC: insert three rows with the same date to verify.
    unit_conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (1, 1.0, "Other", "2026-07-01", "first inserted"),
            (1, 1.0, "Other", "2026-07-01", "second inserted"),
            (1, 1.0, "Other", "2026-07-01", "third inserted"),
        ],
    )
    unit_conn.commit()
    tx = get_recent_transactions(unit_conn, 1, limit=3)
    # All three share 2026-07-01; the most recently inserted (highest id) first.
    descriptions = [t["description"] for t in tx]
    assert descriptions[0] == "third inserted"


def test_get_recent_transactions_empty_list(unit_conn):
    assert get_recent_transactions(unit_conn, 999) == []


def test_get_recent_transactions_limit(unit_conn):
    assert len(get_recent_transactions(unit_conn, 1, limit=2)) == 2


# --------------------------------------------------------------------- #
# get_category_breakdown                                                 #
# --------------------------------------------------------------------- #

def test_get_category_breakdown_ordered_by_amount(unit_conn):
    bd = get_category_breakdown(unit_conn, 1)
    # All 7 CATEGORIES are returned; non-spend categories appear with
    # amount=0 / pct=0, sorted alphabetically among themselves after the
    # three real spenders.
    assert len(bd) == len(CATEGORIES) == 7
    # Hand-rolled fixture: Food=60, Transport=30, Bills=10. The other
    # four categories are zero-spend and tie-break alphabetically.
    assert [r["name"] for r in bd] == [
        "Food", "Transport", "Bills",
        "Entertainment", "Health", "Other", "Shopping",
    ]
    # Non-zero amounts in the expected order.
    assert [r["amount"] for r in bd] == [
        60.0, 30.0, 10.0, 0.0, 0.0, 0.0, 0.0,
    ]


def test_get_category_breakdown_percentages_sum_to_100(unit_conn):
    bd = get_category_breakdown(unit_conn, 1)
    assert sum(r["pct"] for r in bd) == 100
    # 60 + 30 + 10 = 100 -> 60%, 30%, 10%; zero-spend categories at 0%.
    assert [r["pct"] for r in bd] == [60, 30, 10, 0, 0, 0, 0]


def test_get_category_breakdown_empty_user(unit_conn):
    bd = get_category_breakdown(unit_conn, 999)
    assert len(bd) == len(CATEGORIES) == 7
    assert all(r["amount"] == 0.0 for r in bd)
    assert all(r["pct"] == 0 for r in bd)
    assert sum(r["pct"] for r in bd) == 0


def test_get_category_breakdown_rounding_remainder_bumped_to_largest(
    tmp_path, monkeypatch
):
    """When rounded percentages don't sum to 100, the largest-by-amount
    category absorbs the remainder so the list sums to exactly 100."""
    test_db = tmp_path / "remainder.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db))
    init_db()
    c = get_db()
    c.execute(
        "INSERT INTO users (id, name, email, password_hash) "
        "VALUES (1, 'T', 't@x.com', 'x')"
    )
    # Three equal rows of 1 rupee -> raw pct = 33.33 each, rounds to 33, sum=99.
    for desc in ("a", "b", "c"):
        c.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (1, 1.0, ?, '2026-06-30', ?)",
            (["Food", "Transport", "Bills"][["a", "b", "c"].index(desc)], desc),
        )
    c.commit()

    bd = get_category_breakdown(c, 1)
    assert sum(r["pct"] for r in bd) == 100
    # Largest row (tie -> alphabetical -> Bills) absorbs the +1 remainder;
    # the four zero-spend categories trail at 0%.
    assert [r["pct"] for r in bd] == [34, 33, 33, 0, 0, 0, 0]
    c.close()


# --------------------------------------------------------------------- #
# Route: GET /profile                                                    #
# --------------------------------------------------------------------- #

def test_profile_unauthenticated_redirects_to_login(app_client):
    resp = app_client.get("/profile", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_authenticated_renders_live_data(app_client):
    # Log in as the demo user (id=1, password = demo123 per seed_db).
    app_client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
        follow_redirects=False,
    )

    resp = app_client.get("/profile", follow_redirects=False)
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)

    # Account header
    assert "Demo User" in body
    assert "demo@spendly.com" in body

    # Currency glyph and the real seed total.
    # NOTE: the spec claims 346.24; the real seed sums to 300.14.
    # We assert the real value.
    assert "₹" in body
    assert "300.14" in body

    # Activity tiles
    assert ">8<" in body        # transaction count tile
    assert "Bills" in body      # top category

    # Recent expenses table: 8 data rows (one per seed expense)
    assert body.count("<tr>") - body.count("</thead>") >= 8  # header + 8 rows
    # Newest-first: the first data row's date is the most recent seed date.
    # Seed dates are offset from "today" (2026-07-16) by 0/2/5/7/10/14/18/25 days.
    assert "2026-07-16" in body

    # Spending by category: all 7 categories rendered
    for cat in CATEGORIES:
        assert cat in body
