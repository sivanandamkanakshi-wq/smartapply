"""
Application Tracker blueprint for SmartApply.

HOW TO WIRE THIS INTO YOUR EXISTING APP (matches your app.config["DATABASE_PATH"] setup):

1. Save this file as features/application_tracker.py
2. In app.py, add near your other imports:

       from features.application_tracker import tracker_bp, init_tracker_db

   Then, AFTER app.config["DATABASE_PATH"] is set (same place you call init_db()):

       app.register_blueprint(tracker_bp)
       init_tracker_db(app)

3. This module assumes the logged-in user's id is stored in
   session['user_id']. If your login code uses a different key,
   change USER_SESSION_KEY below to match.

4. In dashboard.html, change the Application Tracker card's link
   from the "Not available yet" text to: <a href="{{ url_for('tracker.list_applications') }}">
"""

from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from core import get_db

tracker_bp = Blueprint("tracker", __name__)

# Change this if your login code stores the user id under a different session key
USER_SESSION_KEY = "user_id"

VALID_STATUSES = ["applied", "viewed", "interviewing", "closed"]


def get_conn():
    return get_db()


def init_tracker_db(app):
    """Call once at startup, right after your existing init_db()."""
    if app.config.get("DATABASE_URL"):
        return
    conn = get_db(app.config)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_title TEXT NOT NULL,
            company TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'applied',
            applied_date TEXT NOT NULL,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def current_user_id():
    return session.get(USER_SESSION_KEY)


@tracker_bp.route("/applications")
def list_applications():
    user_id = current_user_id()
    if not user_id:
        return redirect(url_for("login"))  # change "login" to your actual login route name

    status_filter = request.args.get("status", "all")
    conn = get_conn()
    if status_filter in VALID_STATUSES:
        rows = conn.execute(
            "SELECT * FROM applications WHERE user_id = ? AND status = ? ORDER BY applied_date DESC",
            (user_id, status_filter),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM applications WHERE user_id = ? ORDER BY applied_date DESC",
            (user_id,),
        ).fetchall()
    conn.close()

    counts = {}
    conn = get_conn()
    for s in VALID_STATUSES:
        counts[s] = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE user_id = ? AND status = ?",
            (user_id, s),
        ).fetchone()[0]
    conn.close()

    return render_template(
        "applications.html",
        applications=rows,
        counts=counts,
        active_filter=status_filter,
        statuses=VALID_STATUSES,
        today=date.today().isoformat(),
    )


@tracker_bp.route("/applications/add", methods=["POST"])
def add_application():
    user_id = current_user_id()
    if not user_id:
        return redirect(url_for("login"))

    job_title = request.form.get("job_title", "").strip()
    company = request.form.get("company", "").strip()
    applied_date = request.form.get("applied_date") or date.today().isoformat()
    notes = request.form.get("notes", "").strip()

    if not job_title or not company:
        flash("Job title and company are required.")
        return redirect(url_for("tracker.list_applications"))

    conn = get_conn()
    conn.execute(
        "INSERT INTO applications (user_id, job_title, company, status, applied_date, notes) "
        "VALUES (?, ?, ?, 'applied', ?, ?)",
        (user_id, job_title, company, applied_date, notes),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("tracker.list_applications"))


@tracker_bp.route("/applications/<int:app_id>/status", methods=["POST"])
def update_status(app_id):
    user_id = current_user_id()
    if not user_id:
        return redirect(url_for("login"))

    new_status = request.form.get("status")
    if new_status not in VALID_STATUSES:
        flash("Invalid status.")
        return redirect(url_for("tracker.list_applications"))

    conn = get_conn()
    conn.execute(
        "UPDATE applications SET status = ? WHERE id = ? AND user_id = ?",
        (new_status, app_id, user_id),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("tracker.list_applications"))


@tracker_bp.route("/applications/<int:app_id>/delete", methods=["POST"])
def delete_application(app_id):
    user_id = current_user_id()
    if not user_id:
        return redirect(url_for("login"))

    conn = get_conn()
    conn.execute("DELETE FROM applications WHERE id = ? AND user_id = ?", (app_id, user_id))
    conn.commit()
    conn.close()
    return redirect(url_for("tracker.list_applications"))