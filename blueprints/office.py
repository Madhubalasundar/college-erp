from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user

from models import db, Fee, Student, User, Book, BookIssue

office_bp = Blueprint("office", __name__, url_prefix="/office")


@office_bp.before_request
def _guard():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.role_name != "office_staff":
        flash("You do not have permission to access that page.", "danger")
        return redirect(url_for("auth.index"))


@office_bp.route("/dashboard")
def dashboard():
    pending_count = Fee.query.filter(Fee.status != "paid").count()
    collected_today = (
        Fee.query.filter(
            Fee.status == "paid",
            db.func.date(Fee.paid_at) == datetime.utcnow().date(),
        ).count()
    )
    return render_template("office/dashboard.html", pending_count=pending_count, collected_today=collected_today)


@office_bp.route("/fees", methods=["GET", "POST"])
def fee_desk():
    query = request.values.get("roll_no", "").strip()
    student = None
    fees = []

    if query:
        student = Student.query.filter_by(roll_no=query).first()
        if student:
            fees = Fee.query.filter_by(student_id=student.student_id).order_by(Fee.due_date).all()
        else:
            flash("No student found with that roll number.", "warning")

    if request.method == "POST":
        fee_id = request.form.get("fee_id", type=int)
        amount = request.form.get("amount", type=float)
        fee = Fee.query.get_or_404(fee_id)

        fee.amount_paid = min(float(fee.amount_due), float(fee.amount_paid) + amount)
        fee.status = "paid" if fee.amount_paid >= float(fee.amount_due) else "partial"
        fee.receipt_no = fee.receipt_no or f"RCPT-{fee.fee_id}-{int(datetime.utcnow().timestamp())}"
        fee.paid_at = datetime.utcnow()
        db.session.commit()

        flash(f"Payment of ₹{amount:.2f} recorded. Receipt: {fee.receipt_no}", "success")
        return redirect(url_for("office.fee_desk", roll_no=query))

    return render_template("office/fee_desk.html", student=student, fees=fees, query=query)


@office_bp.route("/library", methods=["GET"])
def library():
    query = request.args.get("roll_no", "").strip()
    student = None
    my_issues = []

    if query:
        student = Student.query.filter_by(roll_no=query).first()
        if student:
            my_issues = (
                BookIssue.query.filter_by(student_id=student.student_id, status="issued")
                .order_by(BookIssue.issued_at.desc())
                .all()
            )
        else:
            flash("No student found with that roll number.", "warning")

    available_books = Book.query.filter(Book.available_copies > 0).order_by(Book.title).all()
    all_issued = (
        BookIssue.query.filter_by(status="issued").order_by(BookIssue.issued_at.desc()).limit(50).all()
    )
    return render_template(
        "office/library.html",
        student=student,
        query=query,
        my_issues=my_issues,
        available_books=available_books,
        all_issued=all_issued,
    )


@office_bp.route("/library/issue", methods=["POST"])
def library_issue():
    roll_no = request.form.get("roll_no", "").strip()
    book_id = request.form.get("book_id", type=int)

    student = Student.query.filter_by(roll_no=roll_no).first()
    if not student:
        flash("No student found with that roll number.", "danger")
        return redirect(url_for("office.library", roll_no=roll_no))

    book = Book.query.get_or_404(book_id)
    if book.available_copies < 1:
        flash("No copies of that book are currently available.", "danger")
        return redirect(url_for("office.library", roll_no=roll_no))

    book.available_copies -= 1
    db.session.add(
        BookIssue(
            book_id=book.book_id,
            student_id=student.student_id,
            due_date=date.today() + timedelta(days=14),
        )
    )
    db.session.commit()
    flash(f'"{book.title}" issued to {student.roll_no}.', "success")
    return redirect(url_for("office.library", roll_no=roll_no))


@office_bp.route("/library/return/<int:issue_id>", methods=["POST"])
def library_return(issue_id):
    issue = BookIssue.query.get_or_404(issue_id)
    roll_no = issue.student.roll_no

    if issue.status == "returned":
        flash("This book was already returned.", "info")
        return redirect(url_for("office.library", roll_no=roll_no))

    issue.status = "returned"
    issue.returned_at = datetime.utcnow()
    issue.book.available_copies += 1
    db.session.commit()
    flash(f'"{issue.book.title}" marked as returned.', "success")
    return redirect(url_for("office.library", roll_no=roll_no))
