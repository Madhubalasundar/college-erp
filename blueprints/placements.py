from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from models import db, Placement, PlacementApplication

placements_bp = Blueprint("placements", __name__, url_prefix="/placements")


@placements_bp.before_request
def _guard():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.student_login"))


@placements_bp.route("/")
@login_required
def index():
    if current_user.role_name == "student":
        student = current_user.student_profile
        open_placements = Placement.query.filter(
            Placement.status == "open",
            Placement.application_deadline >= datetime.utcnow().date(),
        ).order_by(Placement.application_deadline).all()

        my_applications = PlacementApplication.query.filter_by(
            student_id=student.student_id
        ).order_by(PlacementApplication.applied_at.desc()).all()

        return render_template(
            "placements/student_list.html",
            open_placements=open_placements,
            my_applications=my_applications,
        )

    elif current_user.role_name in ("admin", "principal", "office_staff"):
        placements = Placement.query.order_by(Placement.created_at.desc()).all()
        return render_template("placements/manage.html", placements=placements)

    flash("Access denied.", "danger")
    return redirect(url_for("auth.index"))


@placements_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if current_user.role_name not in ("admin", "principal", "office_staff"):
        flash("You do not have permission to create placements.", "danger")
        return redirect(url_for("placements.index"))

    if request.method == "POST":
        company = request.form.get("company_name", "").strip()
        role = request.form.get("role", "").strip()
        description = request.form.get("description", "").strip()
        eligibility = request.form.get("eligibility_criteria", "").strip()
        ctc = request.form.get("package_ctc", "").strip()
        deadline_str = request.form.get("application_deadline")
        interview_str = request.form.get("interview_date")
        venue = request.form.get("venue", "").strip()

        if not company or not role or not deadline_str:
            flash("Company, role, and deadline are required.", "danger")
            return redirect(url_for("placements.create"))

        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            interview = datetime.strptime(interview_str, "%Y-%m-%d").date() if interview_str else None
        except ValueError:
            flash("Invalid date format.", "danger")
            return redirect(url_for("placements.create"))

        placement = Placement(
            company_name=company,
            role=role,
            description=description,
            eligibility_criteria=eligibility,
            package_ctc=ctc,
            application_deadline=deadline,
            interview_date=interview,
            venue=venue,
            created_by=current_user.user_id,
        )
        db.session.add(placement)
        db.session.commit()

        from models import AuditLog
        db.session.add(AuditLog(
            user_id=current_user.user_id,
            action="CREATE",
            module="placements",
            details=f"Created placement: {company} - {role}",
        ))
        db.session.commit()

        flash("Placement created.", "success")
        return redirect(url_for("placements.index"))

    return render_template("placements/create.html")


@placements_bp.route("/<int:placement_id>")
@login_required
def view(placement_id):
    placement = Placement.query.get_or_404(placement_id)

    if current_user.role_name == "student":
        student = current_user.student_profile
        application = PlacementApplication.query.filter_by(
            placement_id=placement_id, student_id=student.student_id
        ).first()
        return render_template("placements/student_detail.html", placement=placement, application=application)

    elif current_user.role_name in ("admin", "principal", "office_staff"):
        applications = PlacementApplication.query.filter_by(placement_id=placement_id).all()
        return render_template("placements/detail.html", placement=placement, applications=applications)

    flash("Access denied.", "danger")
    return redirect(url_for("auth.index"))


@placements_bp.route("/<int:placement_id>/apply", methods=["POST"])
@login_required
def apply(placement_id):
    if current_user.role_name != "student":
        flash("Only students can apply.", "danger")
        return redirect(url_for("placements.index"))

    student = current_user.student_profile
    placement = Placement.query.get_or_404(placement_id)

    if placement.status != "open":
        flash("This placement is closed.", "danger")
        return redirect(url_for("placements.index"))

    existing = PlacementApplication.query.filter_by(
        placement_id=placement_id, student_id=student.student_id
    ).first()
    if existing:
        flash("You have already applied for this placement.", "warning")
        return redirect(url_for("placements.view", placement_id=placement_id))

    application = PlacementApplication(
        placement_id=placement_id,
        student_id=student.student_id,
    )
    db.session.add(application)
    db.session.commit()

    flash("Application submitted.", "success")
    return redirect(url_for("placements.view", placement_id=placement_id))


@placements_bp.route("/<int:placement_id>/update/<int:app_id>", methods=["POST"])
@login_required
def update_application(placement_id, app_id):
    if current_user.role_name not in ("admin", "principal", "office_staff"):
        flash("You do not have permission.", "danger")
        return redirect(url_for("placements.index"))

    application = PlacementApplication.query.get_or_404(app_id)
    new_status = request.form.get("status")
    remarks = request.form.get("remarks", "").strip()

    valid_statuses = ("applied", "shortlisted", "interviewed", "selected", "rejected")
    if new_status not in valid_statuses:
        flash("Invalid status.", "danger")
        return redirect(url_for("placements.view", placement_id=placement_id))

    application.status = new_status
    application.remarks = remarks
    db.session.commit()

    flash(f"Application {new_status}.", "success")
    return redirect(url_for("placements.view", placement_id=placement_id))
