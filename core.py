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


class DatabaseConnection:
    def __init__(self, connection, is_postgresql):
        self._connection = connection
        self._is_postgresql = is_postgresql

    def execute(self, query, parameters=()):
        if self._is_postgresql:
            query = query.replace("?", "%s")
        return self._connection.execute(query, parameters)

    def commit(self):
        return self._connection.commit()

    def close(self):
        return self._connection.close()


def is_postgresql(config=None):
    config = config or current_app.config
    return bool(config.get("DATABASE_URL"))


def get_db(config=None):
    """
    Open a database connection using DATABASE_URL when configured, otherwise
    use the local SQLite database path. Callers are responsible for closing it.
    """
    config = config or current_app.config
    if is_postgresql(config):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL support requires the 'psycopg[binary]' package."
            ) from exc
        return DatabaseConnection(
            psycopg.connect(config["DATABASE_URL"], row_factory=dict_row),
            True,
        )

    connection = sqlite3.connect(config["DATABASE_PATH"])
    connection.row_factory = sqlite3.Row
    return DatabaseConnection(connection, False)


def is_integrity_error(error):
    if isinstance(error, sqlite3.IntegrityError):
        return True
    if is_postgresql():
        import psycopg
        return isinstance(error, psycopg.IntegrityError)
    return False


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
