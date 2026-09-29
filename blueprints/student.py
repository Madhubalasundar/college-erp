import os
import uuid
from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import (
    db, Attendance, Marks, Fee, Timetable, Notification, Result,
    LeaveApplication, Book, BookIssue, Complaint,
)

student_bp = Blueprint("student", __name__, url_prefix="/student")

ALLOWED_PHOTO_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5MB


def _allowed_photo_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_PHOTO_EXTENSIONS


def _get_student_profile():
    return current_user.student_profile


@student_bp.before_request
def _guard():
    """Enforce login + student role on every route in this blueprint."""
    if not current_user.is_authenticated:
        return redirect(url_for("auth.student_login"))
    if current_user.role_name != "student":
        flash("You do not have permission to access that page.", "danger")
        return redirect(url_for("auth.index"))


@student_bp.route("/dashboard")
def dashboard():
    student = _get_student_profile()

    total_classes = Attendance.query.filter_by(student_id=student.student_id).count()
    present_classes = Attendance.query.filter_by(student_id=student.student_id, status="present").count()
    attendance_pct = round((present_classes / total_classes) * 100, 1) if total_classes else 0

    pending_fees = Fee.query.filter_by(student_id=student.student_id).filter(
        Fee.status != "paid"
    ).all()
    total_due = sum(float(f.amount_due) - float(f.amount_paid) for f in pending_fees)
    pending_fees_count = len(pending_fees)

    recent_marks = (
        Marks.query.filter_by(student_id=student.student_id)
        .order_by(Marks.graded_at.desc())
        .limit(5)
        .all()
    )

    notifications = (
        Notification.query.filter(
            (Notification.target_role == "all") | (Notification.target_role == "student")
        )
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )

    # Get CGPA from results
    results = Result.query.filter_by(student_id=student.student_id).all()
    cgpa = max((float(r.cgpa) for r in results if r.cgpa is not None), default=0)

    # Pending items
    pending_complaints = Complaint.query.filter_by(
        student_id=student.student_id, status="open"
    ).count()
    pending_leaves = LeaveApplication.query.filter_by(
        applicant_type="student", student_id=student.student_id, status="pending"
    ).count()

    return render_template(
        "student/dashboard.html",
        student=student,
        attendance_pct=attendance_pct,
        total_due=total_due,
        pending_fees_count=pending_fees_count,
        recent_marks=recent_marks,
        notifications=notifications,
        cgpa=cgpa,
        pending_complaints=pending_complaints,
        pending_leaves=pending_leaves,
    )


@student_bp.route("/attendance")
def attendance():
    student = _get_student_profile()
    records = (
        Attendance.query.filter_by(student_id=student.student_id)
        .order_by(Attendance.attendance_date.desc())
        .all()
    )

    by_subject = {}
    for r in records:
        key = r.subject.subject_name
        by_subject.setdefault(key, {"present": 0, "absent": 0, "late": 0, "total": 0})
        by_subject[key][r.status] += 1
        by_subject[key]["total"] += 1

    return render_template("student/attendance.html", records=records, by_subject=by_subject)


@student_bp.route("/marks")
def marks():
    student = _get_student_profile()
    records = (
        Marks.query.filter_by(student_id=student.student_id)
        .order_by(Marks.graded_at.desc())
        .all()
    )
    return render_template("student/marks.html", records=records)


@student_bp.route("/results")
def results():
    student = _get_student_profile()
    rows = (
        Result.query.filter_by(student_id=student.student_id)
        .order_by(Result.semester)
        .all()
    )
    return render_template("student/results.html", results=rows)


@student_bp.route("/fees")
def fees():
    student = _get_student_profile()
    records = Fee.query.filter_by(student_id=student.student_id).order_by(Fee.due_date.desc()).all()
    total_due = sum(float(f.amount_due) - float(f.amount_paid) for f in records)
    return render_template("student/fees.html", records=records, total_due=total_due)


@student_bp.route("/fees/pay/<int:fee_id>", methods=["POST"])
def pay_fee(fee_id):
    student = _get_student_profile()
    fee = Fee.query.filter_by(fee_id=fee_id, student_id=student.student_id).first_or_404()

    if fee.status == "paid":
        flash("This fee has already been paid.", "info")
        return redirect(url_for("student.fees"))

    outstanding = float(fee.amount_due) - float(fee.amount_paid)
    fee.amount_paid = fee.amount_due
    fee.status = "paid"
    fee.receipt_no = fee.receipt_no or f"RCPT-{fee.fee_id}-{int(datetime.utcnow().timestamp())}"
    fee.paid_at = datetime.utcnow()
    db.session.commit()

    flash(f"Payment of ₹{outstanding:.2f} successful. Receipt: {fee.receipt_no}", "success")
    return redirect(url_for("student.fees"))


@student_bp.route("/timetable")
def timetable():
    student = _get_student_profile()
    entries = (
        Timetable.query.filter_by(course_id=student.course_id, semester=student.current_semester)
        .order_by(Timetable.day_of_week, Timetable.start_time)
        .all()
    )
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    grid = {d: [] for d in days}
    for e in entries:
        grid[e.day_of_week].append(e)
    return render_template("student/timetable.html", grid=grid, days=days)


@student_bp.route("/profile")
def profile():
    student = _get_student_profile()
    return render_template("student/profile.html", student=student, user=current_user)


@student_bp.route("/profile/photo/upload", methods=["POST"])
def upload_photo():
    """Upload or replace student profile photo."""
    student = _get_student_profile()

    if "photo" not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for("student.profile"))

    file = request.files["photo"]
    if file.filename == "":
        flash("No file selected.", "danger")
        return redirect(url_for("student.profile"))

    if not _allowed_photo_file(file.filename):
        flash("Invalid file type. Allowed: JPG, JPEG, PNG, WebP", "danger")
        return redirect(url_for("student.profile"))

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_PHOTO_SIZE:
        flash("File too large. Maximum size is 5MB.", "danger")
        return redirect(url_for("student.profile"))

    # Generate secure filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(f"student_{student.student_id}_{uuid.uuid4().hex[:8]}.{ext}")

    # Ensure upload directory exists
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "students")
    os.makedirs(upload_dir, exist_ok=True)

    # Save file
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    # Remove old photo file
    if student.profile_photo:
        old_path = os.path.join(current_app.root_path, "static", student.profile_photo)
        if os.path.exists(old_path):
            os.remove(old_path)

    # Update database
    student.profile_photo = f"uploads/students/{filename}"
    db.session.commit()

    # Audit log
    from models import AuditLog
    db.session.add(AuditLog(
        user_id=current_user.user_id,
        action="UPLOAD",
        module="student_profile",
        details=f"Uploaded profile photo for {student.roll_no}",
    ))
    db.session.commit()

    flash("Profile photo uploaded successfully.", "success")
    return redirect(url_for("student.profile"))


@student_bp.route("/profile/photo/delete", methods=["POST"])
def delete_photo():
    """Remove student profile photo."""
    student = _get_student_profile()

    if not student.profile_photo:
        flash("No profile photo to remove.", "warning")
        return redirect(url_for("student.profile"))

    # Remove file
    file_path = os.path.join(current_app.root_path, "static", student.profile_photo)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Update database
    student.profile_photo = None
    db.session.commit()

    # Audit log
    from models import AuditLog
    db.session.add(AuditLog(
        user_id=current_user.user_id,
        action="DELETE",
        module="student_profile",
        details=f"Removed profile photo for {student.roll_no}",
    ))
    db.session.commit()

    flash("Profile photo removed.", "info")
    return redirect(url_for("student.profile"))


@student_bp.route("/leave", methods=["GET", "POST"])
def leave():
    student = _get_student_profile()

    if request.method == "POST":
        from_date_str = request.form.get("from_date")
        to_date_str = request.form.get("to_date")
        reason = request.form.get("reason", "").strip()
        leave_type = request.form.get("leave_type", "general")

        try:
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            flash("Please provide valid from/to dates.", "danger")
            return redirect(url_for("student.leave"))

        if to_date < from_date:
            flash("To date cannot be before the from date.", "danger")
            return redirect(url_for("student.leave"))
        if not reason:
            flash("Please provide a reason for leave.", "danger")
            return redirect(url_for("student.leave"))

        db.session.add(
            LeaveApplication(
                applicant_type="student",
                student_id=student.student_id,
                leave_type=leave_type,
                from_date=from_date,
                to_date=to_date,
                reason=reason,
            )
        )
        db.session.commit()
        flash("Leave application submitted.", "success")
        return redirect(url_for("student.leave"))

    applications = (
        LeaveApplication.query.filter_by(applicant_type="student", student_id=student.student_id)
        .order_by(LeaveApplication.applied_at.desc())
        .all()
    )
    return render_template("student/leave.html", applications=applications)


@student_bp.route("/library")
def library():
    student = _get_student_profile()
    my_issues = (
        BookIssue.query.filter_by(student_id=student.student_id)
        .order_by(BookIssue.issued_at.desc())
        .all()
    )
    available_books = Book.query.filter(Book.available_copies > 0).order_by(Book.title).all()
    return render_template("student/library.html", my_issues=my_issues, available_books=available_books)


@student_bp.route("/complaints", methods=["GET", "POST"])
def complaints():
    student = _get_student_profile()

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        description = request.form.get("description", "").strip()
        if not subject or not description:
            flash("Please fill in both subject and description.", "danger")
            return redirect(url_for("student.complaints"))

        db.session.add(
            Complaint(student_id=student.student_id, subject=subject, description=description)
        )
        db.session.commit()
        flash("Complaint submitted. The Principal's office will review it.", "success")
        return redirect(url_for("student.complaints"))

    my_complaints = (
        Complaint.query.filter_by(student_id=student.student_id)
        .order_by(Complaint.submitted_at.desc())
        .all()
    )
    return render_template("student/complaints.html", complaints=my_complaints)


@student_bp.route("/notifications")
def notifications():
    student = _get_student_profile()
    all_notifications = (
        Notification.query.filter(
            (Notification.target_role == "all")
            | (Notification.target_role == "student")
        )
        .filter(
            (Notification.dept_id.is_(None)) | (Notification.dept_id == student.course.dept_id)
        )
        .order_by(Notification.created_at.desc())
        .all()
    )
    return render_template("student/notifications.html", notifications=all_notifications)
