from flask import Blueprint, render_template

from core import get_current_user, login_required

saved_jobs_bp = Blueprint("saved_jobs", __name__, url_prefix="/saved-jobs")


@saved_jobs_bp.route("/", methods=["GET"])
@login_required
def saved_jobs():
    user = get_current_user()
    return render_template(
        "features/placeholder.html",
        page_title="Saved Jobs",
        page_icon="💼",
        page_description="Job cards you've bookmarked for later will appear here.",
        active_page="saved_jobs",
        user=user,
    )
