from flask import Blueprint, render_template

from core import get_current_user, login_required

autoapply_bp = Blueprint("autoapply", __name__, url_prefix="/auto-apply")


@autoapply_bp.route("/", methods=["GET"])
@login_required
def ai_auto_apply():
    user = get_current_user()
    return render_template(
        "features/placeholder.html",
        page_title="AI Auto Apply",
        page_icon="🤖",
        page_description="Automated job applications powered by AI — coming soon.",
        active_page="ai_auto_apply",
        user=user,
    )
