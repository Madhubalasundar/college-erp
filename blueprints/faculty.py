import os
import uuid
from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import current_user
from sqlalchemy import func
from werkzeug.utils import secure_filename

from models import db, Attendance, Marks, Student, Subject, Timetable, LeaveApplication, FacultyDocument, FacultyAttendance, Course

faculty_bp = Blueprint("faculty", __name__, url_prefix="/faculty")

ALLOWED_PHOTO_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
ALLOWED_DOC_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'}
MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5MB
MAX_DOC_SIZE = 10 * 1024 * 1024  # 10MB


def _profile():
    return current_user.faculty_profile


@faculty_bp.before_request
def _guard():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.role_name != "faculty":
        flash("You do not have permission to access that page.", "danger")
        return redirect(url_for("auth.index"))


@faculty_bp.route("/dashboard")
def dashboard():
    faculty = _profile()
    my_subjects = Subject.query.join(Timetable, Timetable.subject_id == Subject.subject_id).filter(
        Timetable.faculty_id == faculty.faculty_id
    ).distinct().all()

    today_classes = (
        Timetable.query.filter_by(faculty_id=faculty.faculty_id, day_of_week=date.today().strftime("%a")[:3])
        .order_by(Timetable.start_time)
        .all()
    )

    marks_entered_today = Marks.query.filter(
        Marks.faculty_id == faculty.faculty_id,
        db.func.date(Marks.graded_at) == date.today(),
    ).count()

    return render_template(
        "faculty/dashboard.html",
        faculty=faculty,
        my_subjects=my_subjects,
        today_classes=today_classes,
        marks_entered_today=marks_entered_today,
    )


@faculty_bp.route("/attendance-entry", methods=["GET", "POST"])
def attendance_entry():
    faculty = _profile()
    subjects = Subject.query.join(Timetable, Timetable.subject_id == Subject.subject_id).filter(
        Timetable.faculty_id == faculty.faculty_id
    ).distinct().all()

    selected_subject_id = request.values.get("subject_id", type=int)
    students = []
    if selected_subject_id:
        subject = Subject.query.get_or_404(selected_subject_id)
        students = Student.query.filter_by(course_id=subject.course_id).order_by(Student.roll_no).all()

    if request.method == "POST" and selected_subject_id:
        att_date_str = request.form.get("attendance_date")
        att_date = datetime.strptime(att_date_str, "%Y-%m-%d").date() if att_date_str else date.today()

        for student in students:
            status = request.form.get(f"status_{student.student_id}", "present")
            existing = Attendance.query.filter_by(
                student_id=student.student_id, subject_id=selected_subject_id, attendance_date=att_date
            ).first()
            if existing:
                existing.status = status
            else:
                db.session.add(
                    Attendance(
                        student_id=student.student_id,
                        subject_id=selected_subject_id,
                        faculty_id=faculty.faculty_id,
                        attendance_date=att_date,
                        status=status,
                    )
                )
        db.session.commit()
        flash("Attendance saved successfully.", "success")
        return redirect(url_for("faculty.attendance_entry", subject_id=selected_subject_id))

    return render_template(
        "faculty/attendance_entry.html",
        subjects=subjects,
        students=students,
        selected_subject_id=selected_subject_id,
        today=date.today().isoformat(),
    )


@faculty_bp.route("/marks-entry", methods=["GET", "POST"])
def marks_entry():
    faculty = _profile()
    subjects = Subject.query.join(Timetable, Timetable.subject_id == Subject.subject_id).filter(
        Timetable.faculty_id == faculty.faculty_id
    ).distinct().all()

    selected_subject_id = request.values.get("subject_id", type=int)
    exam_type = request.values.get("exam_type", "internal1")
    students = []
    existing_marks = {}

    if selected_subject_id:
        subject = Subject.query.get_or_404(selected_subject_id)
        students = Student.query.filter_by(course_id=subject.course_id).order_by(Student.roll_no).all()
        rows = Marks.query.filter_by(subject_id=selected_subject_id, exam_type=exam_type).all()
        existing_marks = {r.student_id: r for r in rows}

    if request.method == "POST" and selected_subject_id:
        max_marks = float(request.form.get("max_marks", 100))
        for student in students:
            raw = request.form.get(f"marks_{student.student_id}")
            if raw in (None, ""):
                continue
            score = float(raw)
            record = existing_marks.get(student.student_id)
            if record:
                record.marks_obtained = score
                record.max_marks = max_marks
            else:
                db.session.add(
                    Marks(
                        student_id=student.student_id,
                        subject_id=selected_subject_id,
                        faculty_id=faculty.faculty_id,
                        exam_type=exam_type,
                        marks_obtained=score,
                        max_marks=max_marks,
                    )
                )
        db.session.commit()
        flash("Marks saved successfully.", "success")
        return redirect(url_for("faculty.marks_entry", subject_id=selected_subject_id, exam_type=exam_type))

    return render_template(
        "faculty/marks_entry.html",
        subjects=subjects,
        students=students,
        existing_marks=existing_marks,
        selected_subject_id=selected_subject_id,
        exam_type=exam_type,
    )


@faculty_bp.route("/timetable")
def timetable():
    faculty = _profile()
    entries = (
        Timetable.query.filter_by(faculty_id=faculty.faculty_id)
        .order_by(Timetable.day_of_week, Timetable.start_time)
        .all()
    )
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    grid = {d: [] for d in days}
    for e in entries:
        grid[e.day_of_week].append(e)
    return render_template("faculty/timetable.html", grid=grid, days=days)


@faculty_bp.route("/leave", methods=["GET", "POST"])
def leave():
    faculty = _profile()

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
            return redirect(url_for("faculty.leave"))

        if to_date < from_date:
            flash("To date cannot be before the from date.", "danger")
            return redirect(url_for("faculty.leave"))
        if not reason:
            flash("Please provide a reason for leave.", "danger")
            return redirect(url_for("faculty.leave"))

        db.session.add(
            LeaveApplication(
                applicant_type="faculty",
                faculty_id=faculty.faculty_id,
                leave_type=leave_type,
                from_date=from_date,
                to_date=to_date,
                reason=reason,
            )
        )
        db.session.commit()
        flash("Leave application submitted to your HOD.", "success")
        return redirect(url_for("faculty.leave"))

    applications = (
        LeaveApplication.query.filter_by(applicant_type="faculty", faculty_id=faculty.faculty_id)
        .order_by(LeaveApplication.applied_at.desc())
        .all()
    )
    return render_template("faculty/leave.html", applications=applications)


@faculty_bp.route("/leave-approvals", methods=["GET", "POST"])
def leave_approvals():
    """Faculty approve/reject leave requests from students in their department."""
    faculty = _profile()

    if request.method == "POST":
        leave_id = request.form.get("leave_id", type=int)
        decision = request.form.get("decision")
        remarks = request.form.get("remarks", "").strip()

        app_row = LeaveApplication.query.filter_by(
            leave_id=leave_id, applicant_type="student"
        ).first_or_404()

        if app_row.student.course.dept_id != faculty.dept_id:
            flash("You can only decide on leave requests from your own department.", "danger")
            return redirect(url_for("faculty.leave_approvals"))

        if decision not in ("approved", "rejected"):
            flash("Invalid decision.", "danger")
            return redirect(url_for("faculty.leave_approvals"))

        app_row.status = decision
        app_row.decided_by = current_user.user_id
        app_row.decided_at = datetime.utcnow()
        app_row.decision_remarks = remarks
        db.session.commit()
        flash(f"Leave request {decision}.", "success")
        return redirect(url_for("faculty.leave_approvals"))

    pending = (
        LeaveApplication.query.join(Student, LeaveApplication.student_id == Student.student_id)
        .join(Student.course)
        .filter(LeaveApplication.applicant_type == "student")
        .filter_by(dept_id=faculty.dept_id)
        .order_by(LeaveApplication.applied_at.desc())
        .all()
    )
    return render_template("faculty/leave_approvals.html", applications=pending)


# ---------------------------------------------------------------
# FACULTY PROFILE
# ---------------------------------------------------------------


def _allowed_file(filename, allowed_ext):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_ext


@faculty_bp.route("/profile")
def profile():
    faculty = _profile()
    user = current_user

    # Teaching summary
    my_subjects = Subject.query.join(Timetable, Timetable.subject_id == Subject.subject_id).filter(
        Timetable.faculty_id == faculty.faculty_id
    ).distinct().all()

    total_students = db.session.query(func.count(Student.student_id)).join(
        Subject, Subject.course_id == Student.course_id
    ).join(
        Timetable, Timetable.subject_id == Subject.subject_id
    ).filter(
        Timetable.faculty_id == faculty.faculty_id
    ).scalar() or 0

    # Weekly teaching hours (count of timetable entries as proxy)
    weekly_hours = Timetable.query.filter_by(faculty_id=faculty.faculty_id).count()

    # Workload
    workload = (
        db.session.query(
            Subject.subject_name,
            Subject.subject_code,
            Course.course_name,
            func.count(Timetable.timetable_id).label("hours"),
            func.count(func.distinct(Student.student_id)).label("students"),
        )
        .join(Timetable, Timetable.subject_id == Subject.subject_id)
        .join(Course, Course.course_id == Subject.course_id)
        .outerjoin(Student, Student.course_id == Course.course_id)
        .filter(Timetable.faculty_id == faculty.faculty_id)
        .group_by(Subject.subject_id)
        .all()
    )

    # Attendance
    total_days = FacultyAttendance.query.filter_by(faculty_id=faculty.faculty_id).count()
    present_days = FacultyAttendance.query.filter_by(faculty_id=faculty.faculty_id, status="present").count()
    leave_days = FacultyAttendance.query.filter_by(faculty_id=faculty.faculty_id, status="leave").count()
    attendance_pct = round((present_days / total_days) * 100, 1) if total_days else 0

    # Leave summary
    leave_apps = LeaveApplication.query.filter_by(applicant_type="faculty", faculty_id=faculty.faculty_id).all()
    pending_leaves = sum(1 for l in leave_apps if l.status == "pending")
    approved_leaves = sum(1 for l in leave_apps if l.status == "approved")
    rejected_leaves = sum(1 for l in leave_apps if l.status == "rejected")

    # Documents
    documents = FacultyDocument.query.filter_by(faculty_id=faculty.faculty_id).all()

    # Timetable
    timetable_entries = Timetable.query.filter_by(faculty_id=faculty.faculty_id).order_by(
        Timetable.day_of_week, Timetable.start_time
    ).all()
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    timetable_grid = {d: [] for d in days}
    for e in timetable_entries:
        timetable_grid[e.day_of_week].append(e)

    return render_template(
        "faculty/profile.html",
        faculty=faculty,
        user=user,
        my_subjects=my_subjects,
        total_students=total_students,
        weekly_hours=round(weekly_hours, 1),
        workload=workload,
        total_days=total_days,
        present_days=present_days,
        leave_days=leave_days,
        attendance_pct=attendance_pct,
        pending_leaves=pending_leaves,
        approved_leaves=approved_leaves,
        rejected_leaves=rejected_leaves,
        leave_apps=leave_apps,
        documents=documents,
        timetable_grid=timetable_grid,
        days=days,
    )


@faculty_bp.route("/profile/edit", methods=["GET", "POST"])
def profile_edit():
    faculty = _profile()
    user = current_user

    if request.method == "POST":
        # Only allow editing permitted fields
        user.full_name = request.form.get("full_name", user.full_name).strip()
        user.phone = request.form.get("phone", user.phone).strip()
        user.email = request.form.get("email", user.email).strip()

        faculty.date_of_birth = datetime.strptime(request.form.get("date_of_birth"), "%Y-%m-%d").date() if request.form.get("date_of_birth") else None
        faculty.gender = request.form.get("gender")
        faculty.address = request.form.get("address", "").strip()
        faculty.city = request.form.get("city", "").strip()
        faculty.state = request.form.get("state", "").strip()
        faculty.emergency_contact = request.form.get("emergency_contact", "").strip()
        faculty.qualification = request.form.get("qualification", "").strip()
        faculty.specialization = request.form.get("specialization", "").strip()
        faculty.experience_years = request.form.get("experience_years", type=int, default=0)

        db.session.commit()

        from models import AuditLog
        db.session.add(AuditLog(
            user_id=current_user.user_id,
            action="UPDATE",
            module="faculty_profile",
            details=f"Updated profile for {user.full_name}",
        ))
        db.session.commit()

        flash("Profile updated successfully.", "success")
        return redirect(url_for("faculty.profile"))

    return render_template("faculty/profile_edit.html", faculty=faculty, user=user)


@faculty_bp.route("/profile/photo", methods=["POST"])
def profile_photo():
    faculty = _profile()

    if "photo" not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for("faculty.profile"))

    file = request.files["photo"]
    if file.filename == "":
        flash("No file selected.", "danger")
        return redirect(url_for("faculty.profile"))

    if not _allowed_file(file.filename, ALLOWED_PHOTO_EXTENSIONS):
        flash("Invalid file type. Allowed: JPG, JPEG, PNG, WebP", "danger")
        return redirect(url_for("faculty.profile"))

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_PHOTO_SIZE:
        flash("File too large. Maximum size is 5MB.", "danger")
        return redirect(url_for("faculty.profile"))

    filename = secure_filename(f"faculty_{faculty.faculty_id}_{uuid.uuid4().hex[:8]}.{file.filename.rsplit('.', 1)[1].lower()}")
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "faculty")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    # Remove old photo
    if faculty.profile_photo:
        old_path = os.path.join(current_app.root_path, "static", faculty.profile_photo)
        if os.path.exists(old_path):
            os.remove(old_path)

    faculty.profile_photo = f"uploads/faculty/{filename}"
    db.session.commit()

    flash("Photo updated successfully.", "success")
    return redirect(url_for("faculty.profile"))


@faculty_bp.route("/profile/documents/upload", methods=["POST"])
def document_upload():
    faculty = _profile()

    if "document" not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for("faculty.profile"))

    file = request.files["document"]
    doc_type = request.form.get("document_type")

    if file.filename == "":
        flash("No file selected.", "danger")
        return redirect(url_for("faculty.profile"))

    if not _allowed_file(file.filename, ALLOWED_DOC_EXTENSIONS):
        flash("Invalid file type.", "danger")
        return redirect(url_for("faculty.profile"))

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_DOC_SIZE:
        flash("File too large. Maximum size is 10MB.", "danger")
        return redirect(url_for("faculty.profile"))

    filename = secure_filename(f"doc_{faculty.faculty_id}_{uuid.uuid4().hex[:8]}.{file.filename.rsplit('.', 1)[1].lower()}")
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "faculty_docs")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    doc = FacultyDocument(
        faculty_id=faculty.faculty_id,
        document_type=doc_type,
        file_name=file.filename,
        file_path=f"uploads/faculty_docs/{filename}",
        file_size=file_size,
        description=request.form.get("description", "").strip(),
    )
    db.session.add(doc)
    db.session.commit()

    flash("Document uploaded successfully.", "success")
    return redirect(url_for("faculty.profile"))


@faculty_bp.route("/profile/documents/<int:doc_id>/delete", methods=["POST"])
def document_delete(doc_id):
    doc = FacultyDocument.query.get_or_404(doc_id)

    # Security: only the owner can delete
    if doc.faculty_id != _profile().faculty_id:
        abort(403)

    file_path = os.path.join(current_app.root_path, "static", doc.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(doc)
    db.session.commit()

    flash("Document deleted.", "info")
    return redirect(url_for("faculty.profile"))
