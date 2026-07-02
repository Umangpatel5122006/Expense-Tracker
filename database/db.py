"""SQLite data layer for the Spendly application.

This module exposes three functions:

- :func:`get_db`  — open a connection with row_factory set and foreign keys
  enabled.
- :func:`init_db` — create the ``users`` and ``expenses`` tables (idempotent).
- :func:`seed_db` — populate a single demo user and 8 sample expenses.
  Safe to call multiple times: it short-circuits when the ``users`` table
  already contains rows.

The database file lives in the project root as ``expense_tracker.db``.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

__all__ = ["CATEGORIES", "DB_PATH", "get_db", "init_db", "seed_db"]


# Project root sits one level above this file (database/db.py → project root).
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_PROJECT_ROOT, "expense_tracker.db")

# Fixed list per spec §10. Kept as a tuple so it can be used as a constant
# elsewhere in the app (e.g. for form selects / validation).
CATEGORIES: tuple[str, ...] = (
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
)


def get_db() -> sqlite3.Connection:
    """Open a SQLite connection to the project database.

    Each call returns a fresh connection with:

    - ``row_factory`` set to :class:`sqlite3.Row` for dict-like access;
    - ``PRAGMA foreign_keys = ON`` re-asserted, since this setting is
      per-connection in SQLite and is not persisted across opens.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create the application schema if it does not already exist.

    Uses ``CREATE TABLE IF NOT EXISTS`` so this is safe to call on every
    application start. Two tables are created:

    - ``users``    — id, name, unique email, password hash, created_at.
    - ``expenses`` — id, FK to users, amount, category, date, description,
      created_at.
    """
    conn = get_db()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                email         TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                amount      REAL    NOT NULL,
                category    TEXT    NOT NULL,
                date        TEXT    NOT NULL,
                description TEXT,
                created_at  TEXT    DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db() -> None:
    """Insert the demo user and a fixed set of sample expenses.

    Idempotent: if the ``users`` table is non-empty the function returns
    immediately, so repeated application starts do not duplicate data.

    Seeds:

    - One demo user (``demo@spendly.com`` / password ``demo123``, hashed
      via :func:`werkzeug.security.generate_password_hash`).
    - 8 sample expenses linked to that user, covering all 7 categories
      from :data:`CATEGORIES` (with one repeat), with dates spread across
      the current month.
    """
    conn = get_db()
    try:
        existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing:
            return  # Already seeded — nothing to do.

        # Demo user ------------------------------------------------------------
        password_hash = generate_password_hash("demo123")
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash),
        )
        user_id = cursor.lastrowid

        # Sample expenses ------------------------------------------------------
        # Dates are offset from today so the seeded data always falls within
        # the current month (and therefore looks fresh on every first run).
        today = date.today()
        sample_expenses = [
            (12.50,  "Food",          today - timedelta(days=0),  "Lunch at cafe"),
            (45.00,  "Transport",     today - timedelta(days=2),  "Monthly metro pass"),
            (89.99,  "Bills",         today - timedelta(days=5),  "Internet bill"),
            (32.40,  "Health",        today - timedelta(days=7),  "Pharmacy restock"),
            (15.00,  "Entertainment", today - timedelta(days=10), "Movie ticket"),
            (74.20,  "Shopping",      today - timedelta(days=14), "New running shoes"),
            (8.75,   "Other",         today - timedelta(days=18), "Misc household item"),
            (22.30,  "Food",          today - timedelta(days=25), "Grocery run"),
        ]

        conn.executemany(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(user_id, amount, category, d.isoformat(), description)
             for amount, category, d, description in sample_expenses],
        )
        conn.commit()
    finally:
        conn.close()
