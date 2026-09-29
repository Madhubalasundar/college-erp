from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user
from sqlalchemy import func, case

from models import db, Department, Faculty, Student, Fee, Attendance, Course, Complaint

principal_bp = Blueprint("principal", __name__, url_prefix="/principal")


@principal_bp.before_request
def _guard():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.role_name != "principal":
        flash("You do not have permission to access that page.", "danger")
        return redirect(url_for("auth.index"))


@principal_bp.route("/dashboard")
def dashboard():
    dept_count = Department.query.count()
    faculty_count = Faculty.query.count()
    student_count = Student.query.count()

    total_due = (
        db.session.query(func.sum(Fee.amount_due - Fee.amount_paid))
        .filter(Fee.status != "paid")
        .scalar()
        or 0
    )

    avg_attendance = (
        db.session.query(func.avg(case((Attendance.status == "present", 1), else_=0))).scalar()
    )
    avg_attendance_pct = round((avg_attendance or 0) * 100, 1)

    dept_breakdown = (
        db.session.query(Department.dept_name, func.count(Student.student_id))
        .select_from(Student)
        .join(Course, Student.course_id == Course.course_id)
        .join(Department, Course.dept_id == Department.dept_id)
        .group_by(Department.dept_name)
        .all()
    )

    return render_template(
        "principal/dashboard.html",
        dept_count=dept_count,
        faculty_count=faculty_count,
        student_count=student_count,
        total_due=total_due,
        avg_attendance_pct=avg_attendance_pct,
        dept_breakdown=dept_breakdown,
    )


@principal_bp.route("/finance-overview")
def finance_overview():
    fees = Fee.query.order_by(Fee.due_date.desc()).limit(200).all()
    collected = sum(float(f.amount_paid) for f in fees)
    outstanding = sum(float(f.amount_due) - float(f.amount_paid) for f in fees)
    return render_template("principal/finance.html", fees=fees, collected=collected, outstanding=outstanding)


@principal_bp.route("/attendance-analytics")
def attendance_analytics():
    rows = (
        db.session.query(
            Department.dept_name,
            func.avg(case((Attendance.status == "present", 1), else_=0)).label("avg_present"),
        )
        .select_from(Student)
        .join(Course, Student.course_id == Course.course_id)
        .join(Department, Course.dept_id == Department.dept_id)
        .join(Attendance, Attendance.student_id == Student.student_id)
        .group_by(Department.dept_name)
        .all()
    )
    return render_template("principal/attendance_analytics.html", rows=rows)


@principal_bp.route("/complaints", methods=["GET", "POST"])
def complaints():
    if request.method == "POST":
        complaint_id = request.form.get("complaint_id", type=int)
        new_status = request.form.get("status")
        notes = request.form.get("resolution_notes", "").strip()

        complaint = Complaint.query.get_or_404(complaint_id)
        if new_status not in ("open", "in_progress", "resolved"):
            flash("Invalid status.", "danger")
            return redirect(url_for("principal.complaints"))

        complaint.status = new_status
        complaint.resolution_notes = notes
        if new_status == "resolved":
            complaint.resolved_at = datetime.utcnow()
        else:
            complaint.resolved_at = None
        db.session.commit()
        flash("Complaint updated.", "success")
        return redirect(url_for("principal.complaints"))

    status_filter = request.args.get("status", "")
    query = Complaint.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    all_complaints = query.order_by(Complaint.submitted_at.desc()).all()
    return render_template("principal/complaints.html", complaints=all_complaints, status_filter=status_filter)
