import os
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

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


@app.route("/login")
def login():
    return render_template("login.html")


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
    return "Logout — coming in Step 3"


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
