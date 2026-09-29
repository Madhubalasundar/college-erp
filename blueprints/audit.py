from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from models import db, AuditLog

audit_bp = Blueprint("audit", __name__, url_prefix="/audit")


@audit_bp.before_request
def _guard():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.student_login"))
    if current_user.role_name not in ("admin", "principal"):
        flash("You do not have permission to view audit logs.", "danger")
        return redirect(url_for("auth.index"))


@audit_bp.route("/")
@login_required
def index():
    page = request.args.get("page", 1, type=int)
    module_filter = request.args.get("module", "")
    action_filter = request.args.get("action", "")

    query = AuditLog.query
    if module_filter:
        query = query.filter_by(module=module_filter)
    if action_filter:
        query = query.filter_by(action=action_filter)

    pagination = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )

    # Get distinct modules for filter
    modules = db.session.query(AuditLog.module).distinct().all()
    actions = db.session.query(AuditLog.action).distinct().all()

    return render_template(
        "audit/index.html",
        pagination=pagination,
        module_filter=module_filter,
        action_filter=action_filter,
        modules=[m[0] for m in modules],
        actions=[a[0] for a in actions],
    )
