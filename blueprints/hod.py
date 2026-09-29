import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import current_user
from sqlalchemy import func, case
from werkzeug.utils import secure_filename

from models import db, Faculty, Student, Attendance, Marks, User, Department, LeaveApplication, Subject, Timetable, Course, Result, FacultyDocument, FacultyAttendance

hod_bp = Blueprint("hod", __name__, url_prefix="/hod")

ALLOWED_PHOTO_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
ALLOWED_DOC_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'}
MAX_PHOTO_SIZE = 5 * 1024 * 1024
MAX_DOC_SIZE = 10 * 1024 * 1024


@hod_bp.before_request
def _guard():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.role_name != "hod":
        flash("You do not have permission to access that page.", "danger")
        return redirect(url_for("auth.index"))


def _dept_id():
    return current_user.dept_id


@hod_bp.route("/dashboard")
def dashboard():
    dept_id = _dept_id()
    department = Department.query.get(dept_id)

    faculty_count = Faculty.query.filter_by(dept_id=dept_id).count()
    student_count = (
        Student.query.join(Student.course).filter_by(dept_id=dept_id).count()
    )

    avg_attendance = (
        db.session.query(func.avg(
            case((Attendance.status == "present", 1), else_=0)
        ))
        .join(Student, Attendance.student_id == Student.student_id)
        .join(Student.course)
        .filter_by(dept_id=dept_id)
        .scalar()
    )
    avg_attendance_pct = round((avg_attendance or 0) * 100, 1)

    return render_template(
        "hod/dashboard.html",
        department=department,
        faculty_count=faculty_count,
        student_count=student_count,
        avg_attendance_pct=avg_attendance_pct,
    )


@hod_bp.route("/faculty")
def faculty_management():
    dept_id = _dept_id()
    faculty_list = Faculty.query.filter_by(dept_id=dept_id).join(User).all()
    return render_template("hod/faculty.html", faculty_list=faculty_list)


@hod_bp.route("/student-reports")
def student_reports():
    dept_id = _dept_id()
    students = Student.query.join(Student.course).filter_by(dept_id=dept_id).all()
    return render_template("hod/student_reports.html", students=students)


@hod_bp.route("/department-attendance")
def department_attendance():
    dept_id = _dept_id()
    rows = (
        db.session.query(
            Student.roll_no,
            User.full_name,
            func.count(Attendance.attendance_id).label("total"),
            func.sum(case((Attendance.status == "present", 1), else_=0)).label("present"),
        )
        .join(User, Student.user_id == User.user_id)
        .join(Attendance, Attendance.student_id == Student.student_id)
        .join(Student.course)
        .filter_by(dept_id=dept_id)
        .group_by(Student.student_id)
        .all()
    )
    return render_template("hod/department_attendance.html", rows=rows)


@hod_bp.route("/department-results")
def department_results():
    dept_id = _dept_id()
    rows = (
        db.session.query(
            Student.roll_no,
            User.full_name,
            Marks.exam_type,
            func.avg(Marks.marks_obtained).label("avg_marks"),
        )
        .join(User, Student.user_id == User.user_id)
        .join(Marks, Marks.student_id == Student.student_id)
        .join(Student.course)
        .filter_by(dept_id=dept_id)
        .group_by(Student.student_id, Marks.exam_type)
        .all()
    )
    return render_template("hod/department_results.html", rows=rows)


@hod_bp.route("/leave-approvals", methods=["GET", "POST"])
def leave_approvals():
    """HOD approve/reject leave requests from faculty in their department."""
    dept_id = _dept_id()

    if request.method == "POST":
        leave_id = request.form.get("leave_id", type=int)
        decision = request.form.get("decision")
        remarks = request.form.get("remarks", "").strip()

        app_row = LeaveApplication.query.filter_by(
            leave_id=leave_id, applicant_type="faculty"
        ).first_or_404()

        if app_row.faculty.dept_id != dept_id:
            flash("You can only decide on leave requests from your own department.", "danger")
            return redirect(url_for("hod.leave_approvals"))

        if decision not in ("approved", "rejected"):
            flash("Invalid decision.", "danger")
            return redirect(url_for("hod.leave_approvals"))

        app_row.status = decision
        app_row.decided_by = current_user.user_id
        app_row.decided_at = datetime.utcnow()
        app_row.decision_remarks = remarks
        db.session.commit()
        flash(f"Leave request {decision}.", "success")
        return redirect(url_for("hod.leave_approvals"))

    pending = (
        LeaveApplication.query.join(Faculty, LeaveApplication.faculty_id == Faculty.faculty_id)
        .filter(LeaveApplication.applicant_type == "faculty")
        .filter(Faculty.dept_id == dept_id)
        .order_by(LeaveApplication.applied_at.desc())
        .all()
    )
    return render_template("hod/leave_approvals.html", applications=pending)


# ---------------------------------------------------------------
# HOD PROFILE
# ---------------------------------------------------------------


def _allowed_file(filename, allowed_ext):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_ext


@hod_bp.route("/profile")
def profile():
    hod = current_user.faculty_profile
    user = current_user
    dept_id = _dept_id()
    department = Department.query.get(dept_id)

    # Department stats
    faculty_count = Faculty.query.filter_by(dept_id=dept_id).count()
    student_count = Student.query.join(Student.course).filter_by(dept_id=dept_id).count()
    course_count = Course.query.filter_by(dept_id=dept_id).count()
    subject_count = Subject.query.join(Course).filter_by(dept_id=dept_id).count()

    # Average attendance
    avg_attendance = (
        db.session.query(func.avg(case((Attendance.status == "present", 1), else_=0)))
        .join(Student, Attendance.student_id == Student.student_id)
        .join(Student.course)
        .filter_by(dept_id=dept_id)
        .scalar()
    )
    avg_attendance_pct = round((avg_attendance or 0) * 100, 1)

    # Average CGPA
    avg_cgpa = (
        db.session.query(func.avg(Result.cgpa))
        .join(Student, Result.student_id == Student.student_id)
        .join(Student.course)
        .filter_by(dept_id=dept_id)
        .scalar()
    )
    avg_cgpa = round(float(avg_cgpa), 2) if avg_cgpa else 0

    # Pending requests
    pending_leave = LeaveApplication.query.join(Faculty).filter(
        LeaveApplication.applicant_type == "faculty",
        Faculty.dept_id == dept_id,
        LeaveApplication.status == "pending",
    ).count()

    # Faculty list with workload
    faculty_list = Faculty.query.filter_by(dept_id=dept_id).all()
    faculty_data = []
    for f in faculty_list:
        subjects = Subject.query.join(Timetable).filter(
            Timetable.faculty_id == f.faculty_id
        ).distinct().all()
        hours = Timetable.query.filter_by(faculty_id=f.faculty_id).count()
        faculty_data.append({
            "faculty": f,
            "subjects": subjects,
            "hours": hours,
        })

    # Student year-wise
    current_year = datetime.now().year
    year_counts = {}
    for s in Student.query.join(Student.course).filter_by(dept_id=dept_id).all():
        year = s.current_semester
        year_counts[year] = year_counts.get(year, 0) + 1

    # Low attendance students
    low_attendance = (
        db.session.query(
            Student.roll_no,
            User.full_name,
            func.count(Attendance.attendance_id).label("total"),
            func.sum(case((Attendance.status == "present", 1), else_=0)).label("present"),
        )
        .join(User, Student.user_id == User.user_id)
        .join(Attendance, Attendance.student_id == Student.student_id)
        .join(Student.course)
        .filter_by(dept_id=dept_id)
        .group_by(Student.student_id)
        .having(func.count(Attendance.attendance_id) > 0)
        .all()
    )
    low_attendance_list = []
    for row in low_attendance:
        pct = round((row.present / row.total) * 100, 1) if row.total else 0
        if pct < 75:
            low_attendance_list.append({
                "roll_no": row.roll_no,
                "name": row.full_name,
                "attendance_pct": pct,
            })

    # HOD teaching info
    my_subjects = Subject.query.join(Timetable).filter(
        Timetable.faculty_id == hod.faculty_id
    ).distinct().all()

    # Documents
    documents = FacultyDocument.query.filter_by(faculty_id=hod.faculty_id).all()

    # Timetable
    timetable_entries = Timetable.query.filter_by(faculty_id=hod.faculty_id).order_by(
        Timetable.day_of_week, Timetable.start_time
    ).all()
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    timetable_grid = {d: [] for d in days}
    for e in timetable_entries:
        timetable_grid[e.day_of_week].append(e)

    return render_template(
        "hod/profile.html",
        hod=hod,
        user=user,
        department=department,
        faculty_count=faculty_count,
        student_count=student_count,
        course_count=course_count,
        subject_count=subject_count,
        avg_attendance_pct=avg_attendance_pct,
        avg_cgpa=avg_cgpa,
        pending_leave=pending_leave,
        faculty_data=faculty_data,
        year_counts=year_counts,
        low_attendance_list=low_attendance_list,
        my_subjects=my_subjects,
        documents=documents,
        timetable_grid=timetable_grid,
        days=days,
    )


@hod_bp.route("/profile/edit", methods=["GET", "POST"])
def profile_edit():
    hod = current_user.faculty_profile
    user = current_user

    if request.method == "POST":
        user.full_name = request.form.get("full_name", user.full_name).strip()
        user.phone = request.form.get("phone", user.phone).strip()
        user.email = request.form.get("email", user.email).strip()

        hod.date_of_birth = datetime.strptime(request.form.get("date_of_birth"), "%Y-%m-%d").date() if request.form.get("date_of_birth") else None
        hod.gender = request.form.get("gender")
        hod.address = request.form.get("address", "").strip()
        hod.city = request.form.get("city", "").strip()
        hod.state = request.form.get("state", "").strip()
        hod.emergency_contact = request.form.get("emergency_contact", "").strip()
        hod.qualification = request.form.get("qualification", "").strip()
        hod.specialization = request.form.get("specialization", "").strip()
        hod.experience_years = request.form.get("experience_years", type=int, default=0)

        db.session.commit()

        from models import AuditLog
        db.session.add(AuditLog(
            user_id=current_user.user_id,
            action="UPDATE",
            module="hod_profile",
            details=f"Updated HOD profile for {user.full_name}",
        ))
        db.session.commit()

        flash("Profile updated successfully.", "success")
        return redirect(url_for("hod.profile"))

    return render_template("hod/profile_edit.html", hod=hod, user=user)


@hod_bp.route("/profile/photo", methods=["POST"])
def profile_photo():
    hod = current_user.faculty_profile

    if "photo" not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for("hod.profile"))

    file = request.files["photo"]
    if file.filename == "":
        flash("No file selected.", "danger")
        return redirect(url_for("hod.profile"))

    if not _allowed_file(file.filename, ALLOWED_PHOTO_EXTENSIONS):
        flash("Invalid file type. Allowed: JPG, JPEG, PNG, WebP", "danger")
        return redirect(url_for("hod.profile"))

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_PHOTO_SIZE:
        flash("File too large. Maximum size is 5MB.", "danger")
        return redirect(url_for("hod.profile"))

    filename = secure_filename(f"hod_{hod.faculty_id}_{uuid.uuid4().hex[:8]}.{file.filename.rsplit('.', 1)[1].lower()}")
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "faculty")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    if hod.profile_photo:
        old_path = os.path.join(current_app.root_path, "static", hod.profile_photo)
        if os.path.exists(old_path):
            os.remove(old_path)

    hod.profile_photo = f"uploads/faculty/{filename}"
    db.session.commit()

    flash("Photo updated successfully.", "success")
    return redirect(url_for("hod.profile"))


@hod_bp.route("/profile/documents/upload", methods=["POST"])
def document_upload():
    hod = current_user.faculty_profile

    if "document" not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for("hod.profile"))

    file = request.files["document"]
    doc_type = request.form.get("document_type")

    if file.filename == "":
        flash("No file selected.", "danger")
        return redirect(url_for("hod.profile"))

    if not _allowed_file(file.filename, ALLOWED_DOC_EXTENSIONS):
        flash("Invalid file type.", "danger")
        return redirect(url_for("hod.profile"))

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_DOC_SIZE:
        flash("File too large. Maximum size is 10MB.", "danger")
        return redirect(url_for("hod.profile"))

    filename = secure_filename(f"doc_{hod.faculty_id}_{uuid.uuid4().hex[:8]}.{file.filename.rsplit('.', 1)[1].lower()}")
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "faculty_docs")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    doc = FacultyDocument(
        faculty_id=hod.faculty_id,
        document_type=doc_type,
        file_name=file.filename,
        file_path=f"uploads/faculty_docs/{filename}",
        file_size=file_size,
        description=request.form.get("description", "").strip(),
    )
    db.session.add(doc)
    db.session.commit()

    flash("Document uploaded successfully.", "success")
    return redirect(url_for("hod.profile"))


@hod_bp.route("/profile/documents/<int:doc_id>/delete", methods=["POST"])
def document_delete(doc_id):
    doc = FacultyDocument.query.get_or_404(doc_id)

    if doc.faculty_id != current_user.faculty_profile.faculty_id:
        abort(403)

    file_path = os.path.join(current_app.root_path, "static", doc.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(doc)
    db.session.commit()

    flash("Document deleted.", "info")
    return redirect(url_for("hod.profile"))
