"""
Smart Job Search blueprint for SmartApply — searches real job listings via
the Adzuna API (https://developer.adzuna.com).

HOW TO WIRE THIS INTO YOUR EXISTING APP:

1. Save this file as features/job_search.py

2. In app.py, add near your other imports:
       from features.job_search import job_search_bp

   Then, alongside your other blueprint registrations:
       app.register_blueprint(job_search_bp)

3. Add your Adzuna credentials to .env:
       ADZUNA_APP_ID=your_app_id_here
       ADZUNA_APP_KEY=your_app_key_here
       ADZUNA_COUNTRY=in

   ADZUNA_COUNTRY is the two-letter country code Adzuna uses in its API
   path (e.g. "in" for India, "us" for United States, "gb" for UK) —
   check developer.adzuna.com for the full list of supported countries.

4. Save templates/job_search.html (given separately).

5. In home.html, activate the Smart Job Search card the same way we did
   Application Tracker and Secure Data — link it to
   {{ url_for('job_search.job_search') }} and remove the "Coming soon" badge.
"""

import os
import requests
from flask import Blueprint, render_template, request, session, redirect, url_for, flash

job_search_bp = Blueprint("job_search", __name__)

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "").strip()
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "").strip()
ADZUNA_COUNTRY = (os.getenv("ADZUNA_COUNTRY", "in").strip() or "in").lower()


@job_search_bp.route("/jobs")
def job_search():
    if "user_id" not in session:
        flash("Please log in to continue.")
        return redirect(url_for("login"))

    query = request.args.get("what", "").strip()
    location = request.args.get("where", "").strip()
    jobs = []
    error = None
    searched = bool(query or location)

    if searched:
        if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
            error = "Smart Job Search isn't fully set up yet — add ADZUNA_APP_ID and ADZUNA_APP_KEY to your .env file."
        else:
            params = {
                "app_id": ADZUNA_APP_ID,
                "app_key": ADZUNA_APP_KEY,
                "results_per_page": 20,
                "content-type": "application/json",
                "max_days_old": 30,
                "sort_by": "date",
            }
            if query:
                params["what"] = query
            if location:
                params["where"] = location

            url = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/1"
            try:
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                for item in data.get("results", []):
                    jobs.append({
                        "title": item.get("title", "Untitled role"),
                        "company": (item.get("company") or {}).get("display_name", "Unknown company"),
                        "location": (item.get("location") or {}).get("display_name", ""),
                        "salary_min": item.get("salary_min"),
                        "salary_max": item.get("salary_max"),
                        "description": (item.get("description") or "")[:220],
                        "apply_url": item.get("redirect_url", "#"),
                        "created": (item.get("created") or "")[:10],
                    })
            except requests.exceptions.RequestException as exc:
                print(f"[ADZUNA ERROR] {exc}")
                error = "Something went wrong fetching job listings. Please try again in a moment."

    return render_template(
        "job_search.html",
        jobs=jobs,
        query=query,
        location=location,
        searched=searched,
        error=error,
    )