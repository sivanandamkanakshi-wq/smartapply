from flask import Blueprint, render_template

from core import get_current_user, login_required

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/", methods=["GET"])
@login_required
def analytics():
    user = get_current_user()
    return render_template(
        "features/placeholder.html",
        page_title="Analytics",
        page_icon="📈",
        page_description="Charts, total applications, interviews, and success rate.",
        active_page="analytics",
        user=user,
    )
