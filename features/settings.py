from flask import Blueprint, render_template

from core import get_current_user, login_required

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/", methods=["GET"])
@login_required
def settings():
    user = get_current_user()
    return render_template(
        "features/placeholder.html",
        page_title="Settings",
        page_icon="⚙️",
        page_description="Change password and edit account details will live here.",
        active_page="settings",
        user=user,
    )
