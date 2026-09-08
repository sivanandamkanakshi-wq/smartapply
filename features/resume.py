from flask import Blueprint, render_template

from core import get_current_user, login_required

resume_bp = Blueprint("resume", __name__, url_prefix="/resume")


@resume_bp.route("/", methods=["GET"])
@login_required
def resume_manager():
    user = get_current_user()
    return render_template(
        "features/placeholder.html",
        page_title="Resume Manager",
        page_icon="📄",
        page_description="Upload, view, download, and delete your resumes here.",
        active_page="resume_manager",
        user=user,
    )
