from flask import Blueprint, render_template

from core import get_current_user, login_required

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/create", methods=["GET"])
@login_required
def create_profile():
    user = get_current_user()
    return render_template(
        "features/placeholder.html",
        page_title="Create Profile",
        page_icon="👤",
        page_description="Personal information, education, skills, experience, "
        "projects, and resume upload will live here.",
        active_page="create_profile",
        user=user,
    )
