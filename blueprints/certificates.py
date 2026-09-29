from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from models import db, Certificate

certificates_bp = Blueprint("certificates", __name__, url_prefix="/certificates")


@certificates_bp.before_request
def _guard():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.student_login"))


@certificates_bp.route("/")
@login_required
def index():
    if current_user.role_name == "student":
        certificates = Certificate.query.filter_by(
            student_id=current_user.student_profile.student_id
        ).order_by(Certificate.requested_at.desc()).all()
        return render_template("certificates/student_list.html", certificates=certificates)

    elif current_user.role_name in ("office_staff", "admin", "hod", "principal"):
        status_filter = request.args.get("status", "")
        query = Certificate.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        certificates = query.order_by(Certificate.requested_at.desc()).all()
        return render_template("certificates/manage.html", certificates=certificates, status_filter=status_filter)

    flash("Access denied.", "danger")
    return redirect(url_for("auth.index"))


@certificates_bp.route("/request", methods=["GET", "POST"])
@login_required
def request_certificate():
    if current_user.role_name != "student":
        flash("Only students can request certificates.", "danger")
        return redirect(url_for("certificates.index"))

    if request.method == "POST":
        cert_type = request.form.get("certificate_type")
        purpose = request.form.get("purpose", "").strip()

        if not cert_type:
            flash("Please select a certificate type.", "danger")
            return redirect(url_for("certificates.request_certificate"))

        cert = Certificate(
            student_id=current_user.student_profile.student_id,
            certificate_type=cert_type,
            purpose=purpose,
        )
        db.session.add(cert)
        db.session.commit()

        from models import AuditLog
        db.session.add(AuditLog(
            user_id=current_user.user_id,
            action="REQUEST",
            module="certificates",
            details=f"Requested {cert_type} certificate",
        ))
        db.session.commit()

        flash("Certificate request submitted.", "success")
        return redirect(url_for("certificates.index"))

    return render_template("certificates/request.html")


@certificates_bp.route("/<int:cert_id>/update", methods=["POST"])
@login_required
def update_status(cert_id):
    if current_user.role_name not in ("office_staff", "admin", "hod", "principal"):
        flash("You do not have permission to update certificates.", "danger")
        return redirect(url_for("certificates.index"))

    cert = Certificate.query.get_or_404(cert_id)
    new_status = request.form.get("status")
    remarks = request.form.get("remarks", "").strip()

    valid_statuses = ("requested", "under_review", "approved", "rejected", "generated", "delivered")
    if new_status not in valid_statuses:
        flash("Invalid status.", "danger")
        return redirect(url_for("certificates.index"))

    cert.status = new_status
    cert.remarks = remarks
    cert.resolved_by = current_user.user_id

    if new_status in ("approved", "generated", "delivered", "rejected"):
        cert.resolved_at = datetime.utcnow()

    db.session.commit()

    from models import AuditLog
    db.session.add(AuditLog(
        user_id=current_user.user_id,
        action="UPDATE",
        module="certificates",
        details=f"Certificate {cert_id} status changed to {new_status}",
    ))
    db.session.commit()

    flash(f"Certificate {new_status}.", "success")
    return redirect(url_for("certificates.index"))
