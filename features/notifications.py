from flask import Blueprint, render_template

from core import get_current_user, login_required

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notifications_bp.route("/", methods=["GET"])
@login_required
def notifications():
    user = get_current_user()
    return render_template(
        "features/placeholder.html",
        page_title="Notifications",
        page_icon="🔔",
        page_description="Your notification list will appear here.",
        active_page="notifications",
        user=user,
    )
