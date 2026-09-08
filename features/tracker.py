from flask import Blueprint, render_template

from core import get_current_user, login_required

tracker_bp = Blueprint("tracker", __name__, url_prefix="/tracker")


@tracker_bp.route("/", methods=["GET"])
@login_required
def application_tracker():
    user = get_current_user()
    return render_template(
        "features/placeholder.html",
        page_title="Application Tracker",
        page_icon="📊",
        page_description="Track Applied, Interview, Rejected, and Selected stages.",
        active_page="application_tracker",
        user=user,
    )
