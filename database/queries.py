"""Reusable SQLite query helpers for the /profile view (Step 5 + Step 6).

These helpers:
  - accept an already-open sqlite3 connection (the route owns the lifecycle),
  - never call get_db() or conn.close(),
  - never import Flask,
  - use parameterised SQL exclusively (`?` placeholders),
  - return plain dicts (not sqlite3.Row) so unit tests are easy to write.

The /profile route is the only current consumer; future read-side views
should reuse these helpers rather than duplicating SQL.

Step 6 added optional ``date_from`` / ``date_to`` keyword arguments to the
three read helpers (``get_user_by_id`` is not date-scoped). Both bounds
are inclusive (``date >= ?`` / ``date <= ?``); either may be ``None`` to
mean "no bound on that side". Values are passed through ``?`` placeholders
— never interpolated into the SQL string.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from database.db import CATEGORIES

__all__ = [
    "get_user_by_id",
    "get_summary_stats",
    "get_recent_transactions",
    "get_category_breakdown",
]


# --------------------------------------------------------------------- #
# Users                                                                  #
# --------------------------------------------------------------------- #

def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> dict[str, Any] | None:
    """Return ``{name, email, member_since}`` for a user, or ``None``.

    ``member_since`` is the raw ``users.created_at`` string (e.g.
    ``"2026-07-02 06:23:35"``); the route formats it for display.
    """
    row = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": row["created_at"],
    }


# --------------------------------------------------------------------- #
# Summary stats                                                          #
# --------------------------------------------------------------------- #

def get_summary_stats(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """Return ``{total_spent, transaction_count, top_category}``.

    - ``total_spent`` is a float, ``0.0`` when the user has no expenses
      in the (optional) active range.
    - ``transaction_count`` is an int, ``0`` when the user has no expenses
      in the active range.
    - ``top_category`` is the category with the highest total spend for
      this user, ties broken alphabetically; the em-dash ``"—"`` when
      the user has no expenses in the active range.

    Both ``date_from`` and ``date_to`` are inclusive bounds in
    ``"YYYY-MM-DD"`` form. ``None`` on either side means "no bound".
    """
    where = ["user_id = ?"]
    params: list[Any] = [user_id]
    if date_from is not None:
        where.append("date >= ?")
        params.append(date_from)
    if date_to is not None:
        where.append("date <= ?")
        params.append(date_to)
    where_sql = " AND ".join(where)

    totals = conn.execute(
        f"SELECT COUNT(*), COALESCE(SUM(amount), 0) "
        f"FROM expenses WHERE {where_sql}",
        params,
    ).fetchone()

    top = conn.execute(
        f"SELECT category, SUM(amount) AS total "
        f"FROM expenses WHERE {where_sql} "
        f"GROUP BY category "
        f"ORDER BY total DESC, category ASC "
        f"LIMIT 1",
        params,
    ).fetchone()

    return {
        "total_spent": float(totals[1]),
        "transaction_count": int(totals[0]),
        "top_category": top["category"] if top is not None else "—",
    }


# --------------------------------------------------------------------- #
# Recent transactions                                                   #
# --------------------------------------------------------------------- #

def get_recent_transactions(
    conn: sqlite3.Connection,
    user_id: int,
    limit: int = 10,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict[str, Any]]:
    """Return up to ``limit`` of the user's expenses, newest first.

    Newest is determined by ``(date DESC, id DESC)``: the most recent
    calendar date wins, and on a date tie the most recently inserted
    row (highest ``id``) wins. ``description`` is passed through as
    ``None`` when the column is NULL — the template handles that.

    The ``LIMIT`` is applied **after** the optional date-range WHERE,
    so the cap is "the 10 most recent rows that fall inside the
    range", not "10 most-recent overall that happen to be in range".

    Both ``date_from`` and ``date_to`` are inclusive bounds in
    ``"YYYY-MM-DD"`` form. ``None`` on either side means "no bound".
    """
    where = ["user_id = ?"]
    params: list[Any] = [user_id]
    if date_from is not None:
        where.append("date >= ?")
        params.append(date_from)
    if date_to is not None:
        where.append("date <= ?")
        params.append(date_to)
    where_sql = " AND ".join(where)

    rows = conn.execute(
        f"SELECT date, description, category, amount "
        f"FROM expenses WHERE {where_sql} "
        f"ORDER BY date DESC, id DESC LIMIT ?",
        [*params, limit],
    ).fetchall()
    return [
        {
            "date": r["date"],
            "description": r["description"],
            "category": r["category"],
            "amount": r["amount"],
        }
        for r in rows
    ]


# --------------------------------------------------------------------- #
# Category breakdown                                                     #
# --------------------------------------------------------------------- #

def get_category_breakdown(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict[str, Any]]:
    """Return all 7 :data:`CATEGORIES` with ``{name, amount, pct}``.

    The list is ordered by ``amount DESC`` (ties broken alphabetically by
    category name). Every category from :data:`database.db.CATEGORIES`
    appears in the result — categories with no spend in the (optional)
    active range show ``amount=0.0`` and ``pct=0``.

    The integer ``pct`` values sum to **exactly 100** for any non-empty
    range. The algorithm:

      1. ``total = sum(amounts)`` across all categories in range.
      2. ``pct_i = round(amount_i / total * 100)`` for each category.
      3. ``delta = 100 - sum(pcts)``. ``delta`` lies in ``{-6..+6}`` for
         any 7-row breakdown.
      4. Add ``delta`` to the first row's ``pct`` (largest by amount —
         the list is already sorted by amount DESC). This keeps every
         ``pct`` in ``[0, 100]`` because the bump is bounded by ±6.

    Both ``date_from`` and ``date_to`` are inclusive bounds in
    ``"YYYY-MM-DD"`` form. ``None`` on either side means "no bound".
    """
    where = ["user_id = ?"]
    params: list[Any] = [user_id]
    if date_from is not None:
        where.append("date >= ?")
        params.append(date_from)
    if date_to is not None:
        where.append("date <= ?")
        params.append(date_to)
    where_sql = " AND ".join(where)

    raw = conn.execute(
        f"SELECT category, COALESCE(SUM(amount), 0) AS total "
        f"FROM expenses WHERE {where_sql} "
        f"GROUP BY category",
        params,
    ).fetchall()
    by_cat: dict[str, float] = {r["category"]: float(r["total"]) for r in raw}

    # Order by amount DESC; alphabetical tie-break uses the CATEGORIES
    # tuple's natural ordering (Food, Transport, Bills, Health, ...).
    ordered_cats = sorted(
        CATEGORIES,
        key=lambda c: (-by_cat.get(c, 0.0), c),
    )

    amounts = [by_cat.get(c, 0.0) for c in ordered_cats]
    total = sum(amounts)

    if total == 0.0:
        pcts = [0 for _ in ordered_cats]
    else:
        pcts = [round(a / total * 100) for a in amounts]
        delta = 100 - sum(pcts)
        if delta != 0 and pcts:
            pcts[0] += delta  # largest-by-amount absorbs the remainder

    return [
        {"name": c, "amount": by_cat.get(c, 0.0), "pct": p}
        for c, p in zip(ordered_cats, pcts)
    ]
