from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from models import db, Assignment, AssignmentSubmission, Subject, Student

assignments_bp = Blueprint("assignments", __name__, url_prefix="/assignments")


@assignments_bp.before_request
def _guard():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.student_login"))


@assignments_bp.route("/")
@login_required
def index():
    """Students see their assignments, faculty see created assignments."""
    if current_user.role_name == "student":
        student = current_user.student_profile
        assignments = (
            Assignment.query.join(Subject)
            .filter(Subject.course_id == student.course_id)
            .filter(Assignment.subject.has(semester=student.current_semester))
            .order_by(Assignment.due_date)
            .all()
        )
        # Get submission status for each
        submission_map = {}
        for a in assignments:
            sub = AssignmentSubmission.query.filter_by(
                assignment_id=a.assignment_id, student_id=student.student_id
            ).first()
            submission_map[a.assignment_id] = sub
        return render_template(
            "assignments/student_list.html",
            assignments=assignments,
            submission_map=submission_map,
            today=date.today(),
        )

    elif current_user.role_name == "faculty":
        faculty = current_user.faculty_profile
        assignments = (
            Assignment.query.filter_by(faculty_id=faculty.faculty_id)
            .order_by(Assignment.due_date.desc())
            .all()
        )
        return render_template(
            "assignments/faculty_list.html",
            assignments=assignments,
            today=date.today(),
        )

    flash("Access denied.", "danger")
    return redirect(url_for("auth.index"))


@assignments_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Faculty create assignments."""
    if current_user.role_name != "faculty":
        flash("Only faculty can create assignments.", "danger")
        return redirect(url_for("assignments.index"))

    faculty = current_user.faculty_profile
    subjects = Subject.query.join(
        db.table("timetable"),
        db.text("timetable.subject_id = subjects.subject_id")
    ).filter(
        db.text(f"timetable.faculty_id = {faculty.faculty_id}")
    ).distinct().all()

    if request.method == "POST":
        subject_id = request.form.get("subject_id", type=int)
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        max_marks = request.form.get("max_marks", type=float, default=100)
        due_date_str = request.form.get("due_date")

        if not subject_id or not title or not due_date_str:
            flash("Subject, title, and due date are required.", "danger")
            return redirect(url_for("assignments.create"))

        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid due date.", "danger")
            return redirect(url_for("assignments.create"))

        assignment = Assignment(
            subject_id=subject_id,
            faculty_id=faculty.faculty_id,
            title=title,
            description=description,
            max_marks=max_marks,
            due_date=due_date,
        )
        db.session.add(assignment)
        db.session.commit()

        # Audit log
        from models import AuditLog
        db.session.add(AuditLog(
            user_id=current_user.user_id,
            action="CREATE",
            module="assignments",
            details=f"Created assignment: {title}",
        ))
        db.session.commit()

        flash("Assignment created successfully.", "success")
        return redirect(url_for("assignments.index"))

    return render_template("assignments/create.html", subjects=subjects)


@assignments_bp.route("/<int:assignment_id>")
@login_required
def view(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)

    if current_user.role_name == "student":
        student = current_user.student_profile
        submission = AssignmentSubmission.query.filter_by(
            assignment_id=assignment_id, student_id=student.student_id
        ).first()
        return render_template("assignments/student_detail.html", assignment=assignment, submission=submission)

    elif current_user.role_name == "faculty":
        submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment_id).all()
        return render_template("assignments/faculty_detail.html", assignment=assignment, submissions=submissions)

    flash("Access denied.", "danger")
    return redirect(url_for("auth.index"))


@assignments_bp.route("/<int:assignment_id>/submit", methods=["POST"])
@login_required
def submit(assignment_id):
    """Student submits assignment."""
    if current_user.role_name != "student":
        flash("Only students can submit assignments.", "danger")
        return redirect(url_for("assignments.index"))

    student = current_user.student_profile
    assignment = Assignment.query.get_or_404(assignment_id)

    existing = AssignmentSubmission.query.filter_by(
        assignment_id=assignment_id, student_id=student.student_id
    ).first()

    file_name = request.form.get("file_name", "").strip()
    is_late = date.today() > assignment.due_date

    if existing:
        existing.file_name = file_name or existing.file_name
        existing.status = "late" if is_late else "submitted"
        existing.submitted_at = datetime.utcnow()
    else:
        submission = AssignmentSubmission(
            assignment_id=assignment_id,
            student_id=student.student_id,
            file_name=file_name,
            status="late" if is_late else "submitted",
        )
        db.session.add(submission)

    db.session.commit()
    flash("Assignment submitted.", "success")
    return redirect(url_for("assignments.view", assignment_id=assignment_id))


@assignments_bp.route("/<int:assignment_id>/grade/<int:submission_id>", methods=["POST"])
@login_required
def grade_submission(assignment_id, submission_id):
    """Faculty grades a submission."""
    if current_user.role_name != "faculty":
        flash("Only faculty can grade submissions.", "danger")
        return redirect(url_for("assignments.index"))

    submission = AssignmentSubmission.query.get_or_404(submission_id)
    marks = request.form.get("marks_obtained", type=float)
    feedback = request.form.get("feedback", "").strip()

    if marks is not None:
        submission.marks_obtained = marks
        submission.feedback = feedback
        submission.status = "graded"
        db.session.commit()

        # Audit log
        from models import AuditLog
        db.session.add(AuditLog(
            user_id=current_user.user_id,
            action="GRADE",
            module="assignments",
            details=f"Graded submission {submission_id} for assignment {assignment_id}",
        ))
        db.session.commit()

        flash("Marks saved.", "success")

    return redirect(url_for("assignments.view", assignment_id=assignment_id))
