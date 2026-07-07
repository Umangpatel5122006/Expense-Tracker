import os
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db

app = Flask(__name__)
# Flask `session` requires a secret_key. Read from the environment so a
# production deploy can override it; fall back to a dev-only default.
app.secret_key = os.environ.get("SPENDLY_SECRET_KEY", "dev-only-change-me")


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
    return "Profile page — coming in Step 4"


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
