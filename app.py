import os
import sqlite3
from datetime import datetime

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db, CATEGORIES
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
    add_expense as db_add_expense,
)

app = Flask(__name__)
# Flask `session` requires a secret_key. Read from the environment so a
# production deploy can override it; fall back to a dev-only default.
app.secret_key = os.environ.get("SPENDLY_SECRET_KEY", "dev-only-change-me")


# ------------------------------------------------------------------ #
# Date helpers — used by the /profile date-range filter (Step 6)     #
# ------------------------------------------------------------------ #

def parse_date_range(from_str: str | None, to_str: str | None) -> tuple[str | None, str | None]:
    """Normalize and validate a date range.

    Treats None or empty/whitespace strings as None.
    Parses values as YYYY-MM-DD; if parsing fails, that bound is dropped.
    Re-serializes parsed dates to ensure strict YYYY-MM-DD padding (e.g. 2026-7-5 -> 2026-07-05).
    If both are present and from > to, they are swapped.
    """
    def normalize(value: str | None) -> str | None:
        if not value or not value.strip():
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            return None

    date_from = normalize(from_str)
    date_to = normalize(to_str)

    if date_from and date_to and date_from > date_to:
        date_from, date_to = date_to, date_from

    return date_from, date_to


def _format_range_label(date_from: str | None, date_to: str | None) -> str:
    """Return a human label for the active date range.

    ``all time``        — neither bound set.
    ``since <date>``    — only ``date_from`` set.
    ``until <date>``    — only ``date_to`` set.
    ``<from> – <to>``   — both set (en-dash, U+2013).

    Dates render in the same cross-platform ``9 July 2026`` format
    used for ``member_since`` (the ``%-d`` directive fails on Windows).
    """
    def fmt(value: str) -> str:
        return (
            datetime.strptime(value, "%Y-%m-%d")
            .strftime("%d %B %Y")
            .lstrip("0")
        )

    if date_from and date_to:
        return f"{fmt(date_from)} – {fmt(date_to)}"
    if date_from:
        return f"since {fmt(date_from)}"
    if date_to:
        return f"until {fmt(date_to)}"
    return "all time"


# ------------------------------------------------------------------ #
# Database bootstrap — runs once at import time                       #
# ------------------------------------------------------------------ #
# Ensure the schema exists and the demo data is in place before any
# route is hit. The app context is required for any future helpers
# that may rely on `current_app`; harmless for the current implementation.
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    # Already signed in — bounce to landing rather than show a form for
    # an active session.
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("register.html")

    # POST ---------------------------------------------------------------
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    def fail(msg):
        # On validation failure: re-render with the error and preserve the
        # name/email the user typed (never the password).
        return render_template(
            "register.html", error=msg, name=name, email=email
        ), 200

    # --- name -----------------------------------------------------------
    if not name:
        return fail("Name is required.")
    if len(name) > 100:
        return fail("Name must be 100 characters or fewer.")

    # --- email ----------------------------------------------------------
    if not email or len(email) > 254 or email.count("@") != 1:
        return fail("Please enter a valid email address.")
    local, _, domain = email.partition("@")
    if not local or not domain:
        return fail("Please enter a valid email address.")

    # --- password -------------------------------------------------------
    if len(password) < 8:
        return fail("Password must be at least 8 characters.")

    # --- insert ---------------------------------------------------------
    password_hash = generate_password_hash(password)
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        return fail("An account with that email already exists.")
    finally:
        conn.close()

    # --- success --------------------------------------------------------
    session["user_id"] = user_id
    return redirect(url_for("landing"))


@app.route("/login", methods=["GET", "POST"])
def login():
    # Already signed in — bounce to landing rather than show a form for
    # an active session.
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("login.html")

    # POST ---------------------------------------------------------------
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    def fail(msg):
        # On validation/auth failure: re-render with the error and preserve
        # the email the user typed (never the password). Same error for
        # "no such email" and "wrong password" to avoid leaking which
        # accounts are registered.
        return render_template("login.html", error=msg, email=email), 200

    # --- empty input short-circuits before any DB lookup ----------------
    if not email or not password:
        return fail("Please enter both email and password.")

    # --- look up user by email ------------------------------------------
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()

    if row is None or not check_password_hash(row["password_hash"], password):
        return fail("Invalid email or password.")

    # --- success --------------------------------------------------------
    session["user_id"] = row["id"]
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    # 1. Auth gate — no DB work if not signed in. Filter parsing happens
    #    AFTER the redirect so an unauthenticated request with a query
    #    string still goes straight to /login.
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    # 2. Parse optional ?from=YYYY-MM-DD&to=YYYY-MM-DD query parameters.
    #    Bad values are silently dropped (not 400) so a malformed link
    #    in an email can't break the page.
    date_from, date_to = parse_date_range(request.args.get("from"), request.args.get("to"))

    # 3. One connection, shared by every helper. The route owns open/close;
    #    helpers in database.queries never call get_db() or conn.close().
    conn = get_db()
    try:
        user = get_user_by_id(conn, user_id)

        # 4. Stale session — clear and bounce to login (no 500).
        if user is None:
            session.clear()
            return redirect(url_for("login"))

        stats = get_summary_stats(
            conn, user_id, date_from=date_from, date_to=date_to
        )
        transactions = get_recent_transactions(
            conn, user_id, date_from=date_from, date_to=date_to
        )  # limit=10 default
        categories = get_category_breakdown(
            conn, user_id, date_from=date_from, date_to=date_to
        )
    finally:
        conn.close()

    # 5. Cross-platform date format: "9 July 2026" (no leading zero).
    #    %-d fails on Windows and #d fails on Unix; using %d + lstrip("0")
    #    works on every platform.
    member_since = (
        datetime.strptime(user["member_since"], "%Y-%m-%d %H:%M:%S")
        .strftime("%d %B %Y")
        .lstrip("0")
    )

    # 6. Human-readable range label for the Activity stat-tile meta.
    range_label = _format_range_label(date_from, date_to)

    # 7. Render. The template uses user["name"] / user["email"] for the
    #    account header; recent_transactions and category_breakdown feed
    #    the "Recent expenses" and "Spending by category" sections. The
    #    filter form is rendered above the Recent expenses card.
    return render_template(
        "profile.html",
        user={"name": user["name"], "email": user["email"]},
        member_since=member_since,
        expense_count=stats["transaction_count"],
        total_spent=stats["total_spent"],
        top_category=stats["top_category"],
        recent_transactions=transactions,
        category_breakdown=categories,
        date_from=date_from,
        date_to=date_to,
        range_label=range_label,
        filter_active=bool(date_from or date_to),
    )


@app.route("/analytics")
def analytics():
    # Auth gate
    if session.get("user_id") is None:
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    # Auth gate
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            categories=CATEGORIES,
            date=datetime.now().strftime("%Y-%m-%d"),
        )

    # POST ---------------------------------------------------------------
    amount_raw = request.form.get("amount") or ""
    category = request.form.get("category") or ""
    date = request.form.get("date") or ""
    description = (request.form.get("description") or "").strip()

    def fail(msg):
        return render_template(
            "add_expense.html",
            error=msg,
            categories=CATEGORIES,
            amount=amount_raw,
            category=category,
            date=date,
            description=description,
        ), 200

    # --- validation ------------------------------------------------------
    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError()
    except ValueError:
        return fail("Please enter a valid positive amount.")

    if category not in CATEGORIES:
        return fail("Please select a valid category.")

    if not date:
        return fail("Date is required.")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return fail("Please enter a valid date in YYYY-MM-DD format.")

    # --- insert ---------------------------------------------------------
    conn = get_db()
    try:
        db_add_expense(conn, user_id, amount, category, date, description)
        conn.commit()
    finally:
        conn.close()

    return redirect(url_for("profile"))



@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
