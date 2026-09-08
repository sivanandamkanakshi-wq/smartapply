from flask import Blueprint, render_template

from core import get_current_user, login_required

jobsearch_bp = Blueprint("jobsearch", __name__, url_prefix="/jobs")


@jobsearch_bp.route("/search", methods=["GET"])
@login_required
def job_search():
    user = get_current_user()
    return render_template(
        "features/placeholder.html",
        page_title="Smart Job Search",
        page_icon="🔍",
        page_description="Search bar, filters, and job cards will live here.",
        active_page="job_search",
        user=user,
    )
