"""
core.py — shared helpers used by app.py AND every feature blueprint.

Why this file exists:
Feature blueprints (features/profile.py, features/resume.py, ...) need
`login_required` and `get_current_user()`. If they imported those directly
from app.py, and app.py imports the blueprints to register them, you'd get
a circular import. Putting the shared pieces here breaks that cycle:

    app.py         imports core  (fine)
    features/*.py  imports core  (fine)
    core.py        imports nothing from app.py or features/  (breaks cycle)
"""

import sqlite3
from functools import wraps

from flask import current_app, flash, redirect, session, url_for


def get_db():
    """
    Open a new sqlite3 connection using the path stored in app.config.
    Callers are responsible for closing the connection.
    """
    conn = sqlite3.connect(current_app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row
    return conn


def get_current_user():
    """
    Returns the sqlite3.Row for the logged-in user, or None if there is no
    session or the user no longer exists in the DB.
    """
    user_id = session.get("user_id")
    if not user_id:
        return None

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def login_required(view_func):
    """
    Drop-in replacement for repeating:
        if "user_id" not in session:
            flash("Please log in to continue.")
            return redirect(url_for("login"))
    at the top of every route. Use it as:

        @app.route("/home")
        @login_required
        def home():
            ...
    """

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped
