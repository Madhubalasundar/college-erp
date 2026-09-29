from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user

from models import (
    db, User, Role, Department, Course, Subject, Student, Faculty, ALL_ROLES,
    Book, Notification,
)

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/admin")


@admin_bp.before_request
def _guard():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.role_name != "admin":
        flash("You do not have permission to access that page.", "danger")
        return redirect(url_for("auth.index"))


@admin_bp.route("/dashboard")
def dashboard():
    stats = {
        "students": Student.query.count(),
        "faculty": Faculty.query.count(),
        "departments": Department.query.count(),
        "courses": Course.query.count(),
        "users": User.query.count(),
    }
    return render_template("admin/dashboard.html", stats=stats)


# ---------------------------------------------------------------
# USERS (create/read/update/delete + search + filter)
# ---------------------------------------------------------------

@admin_bp.route("/users")
def users_list():
    q = request.args.get("q", "").strip()
    role_filter = request.args.get("role", "")
    page = request.args.get("page", 1, type=int)

    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            (User.full_name.ilike(like)) | (User.username.ilike(like)) | (User.email.ilike(like))
        )
    if role_filter:
        query = query.join(Role).filter(Role.role_name == role_filter)

    pagination = query.order_by(User.user_id.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template(
        "admin/users_list.html", pagination=pagination, q=q, role_filter=role_filter, roles=ALL_ROLES
    )


@admin_bp.route("/users/new", methods=["GET", "POST"])
def users_new():
    departments = Department.query.all()
    courses = Course.query.order_by(Course.course_name).all()

    if request.method == "POST":
        role = Role.query.filter_by(role_name=request.form["role_name"]).first()
        if not role:
            flash("Invalid role selected.", "danger")
            return redirect(url_for("admin_bp.users_new"))

        # Validate role-specific required fields BEFORE creating anything,
        # so we never end up with a User that has no matching profile row.
        if role.role_name == "student":
            roll_no = request.form.get("roll_no", "").strip()
            course_id = request.form.get("course_id", type=int)
            admission_year = request.form.get("admission_year", type=int)
            if not roll_no or not course_id or not admission_year:
                flash("Roll number, course, and admission year are required for a student account.", "danger")
                return redirect(url_for("admin_bp.users_new"))
            if Student.query.filter_by(roll_no=roll_no).first():
                flash(f"Roll number '{roll_no}' is already in use.", "danger")
                return redirect(url_for("admin_bp.users_new"))

        if role.role_name == "faculty":
            employee_code = request.form.get("employee_code", "").strip()
            dept_id_for_faculty = request.form.get("dept_id", type=int)
            if not employee_code or not dept_id_for_faculty:
                flash("Employee code and department are required for a faculty account.", "danger")
                return redirect(url_for("admin_bp.users_new"))
            if Faculty.query.filter_by(employee_code=employee_code).first():
                flash(f"Employee code '{employee_code}' is already in use.", "danger")
                return redirect(url_for("admin_bp.users_new"))

        if User.query.filter_by(username=request.form["username"].strip()).first():
            flash("That username is already taken.", "danger")
            return redirect(url_for("admin_bp.users_new"))

        user = User(
            username=request.form["username"].strip(),
            email=request.form["email"].strip(),
            full_name=request.form["full_name"].strip(),
            phone=request.form.get("phone", "").strip(),
            role_id=role.role_id,
            dept_id=request.form.get("dept_id", type=int) or None,
        )
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.flush()  # get user.user_id without committing yet

        # Create the linked profile row the rest of the app depends on.
        if role.role_name == "student":
            db.session.add(Student(
                user_id=user.user_id,
                roll_no=request.form["roll_no"].strip(),
                course_id=request.form.get("course_id", type=int),
                current_semester=request.form.get("current_semester", type=int) or 1,
                admission_year=request.form.get("admission_year", type=int),
                guardian_name=request.form.get("guardian_name", "").strip() or None,
                guardian_phone=request.form.get("guardian_phone", "").strip() or None,
                address=request.form.get("address", "").strip() or None,
            ))
        elif role.role_name == "faculty":
            date_joined_str = request.form.get("date_joined", "").strip()
            date_joined = None
            if date_joined_str:
                try:
                    date_joined = datetime.strptime(date_joined_str, "%Y-%m-%d").date()
                except ValueError:
                    date_joined = None
            db.session.add(Faculty(
                user_id=user.user_id,
                employee_code=request.form["employee_code"].strip(),
                dept_id=request.form.get("dept_id", type=int),
                designation=request.form.get("designation", "").strip() or None,
                date_joined=date_joined,
            ))

        db.session.commit()
        flash(f"User {user.username} created.", "success")
        return redirect(url_for("admin_bp.users_list"))

    return render_template(
        "admin/users_form.html", user=None, departments=departments, courses=courses, roles=ALL_ROLES
    )


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
def users_edit(user_id):
    user = User.query.get_or_404(user_id)
    departments = Department.query.all()

    if request.method == "POST":
        user.full_name = request.form["full_name"].strip()
        user.email = request.form["email"].strip()
        user.phone = request.form.get("phone", "").strip()
        user.dept_id = request.form.get("dept_id", type=int) or None
        user.is_active_flag = bool(request.form.get("is_active"))
        new_password = request.form.get("password", "").strip()
        if new_password:
            user.set_password(new_password)
        db.session.commit()
        flash(f"User {user.username} updated.", "success")
        return redirect(url_for("admin_bp.users_list"))

    return render_template("admin/users_form.html", user=user, departments=departments, roles=ALL_ROLES)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
def users_delete(user_id):
    user = User.query.get_or_404(user_id)
    if user.user_id == current_user.user_id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin_bp.users_list"))
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "info")
    return redirect(url_for("admin_bp.users_list"))


# ---------------------------------------------------------------
# DEPARTMENTS (CRUD)
# ---------------------------------------------------------------

@admin_bp.route("/departments", methods=["GET", "POST"])
def departments():
    if request.method == "POST":
        dept = Department(
            dept_name=request.form["dept_name"].strip(),
            dept_code=request.form["dept_code"].strip().upper(),
        )
        db.session.add(dept)
        db.session.commit()
        flash("Department added.", "success")
        return redirect(url_for("admin_bp.departments"))

    all_departments = Department.query.order_by(Department.dept_name).all()
    return render_template("admin/departments.html", departments=all_departments)


@admin_bp.route("/departments/<int:dept_id>/edit", methods=["POST"])
def departments_edit(dept_id):
    dept = Department.query.get_or_404(dept_id)
    dept.dept_name = request.form["dept_name"].strip()
    dept.dept_code = request.form["dept_code"].strip().upper()
    db.session.commit()
    flash("Department updated.", "success")
    return redirect(url_for("admin_bp.departments"))


@admin_bp.route("/departments/<int:dept_id>/delete", methods=["POST"])
def departments_delete(dept_id):
    dept = Department.query.get_or_404(dept_id)
    db.session.delete(dept)
    db.session.commit()
    flash("Department deleted.", "info")
    return redirect(url_for("admin_bp.departments"))


# ---------------------------------------------------------------
# COURSES (CRUD)
# ---------------------------------------------------------------

@admin_bp.route("/courses", methods=["GET", "POST"])
def courses():
    if request.method == "POST":
        course = Course(
            course_name=request.form["course_name"].strip(),
            course_code=request.form["course_code"].strip().upper(),
            dept_id=request.form["dept_id"],
            duration_years=request.form.get("duration_years", type=int, default=4),
        )
        db.session.add(course)
        db.session.commit()
        flash("Course added.", "success")
        return redirect(url_for("admin_bp.courses"))

    all_courses = Course.query.order_by(Course.course_name).all()
    departments = Department.query.all()
    return render_template("admin/courses.html", courses=all_courses, departments=departments)


@admin_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
def courses_delete(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash("Course deleted.", "info")
    return redirect(url_for("admin_bp.courses"))


# ---------------------------------------------------------------
# SUBJECTS (CRUD)
# ---------------------------------------------------------------

@admin_bp.route("/subjects", methods=["GET", "POST"])
def subjects():
    if request.method == "POST":
        subject = Subject(
            subject_name=request.form["subject_name"].strip(),
            subject_code=request.form["subject_code"].strip().upper(),
            course_id=request.form["course_id"],
            semester=request.form.get("semester", type=int),
            credits=request.form.get("credits", type=int, default=3),
        )
        db.session.add(subject)
        db.session.commit()
        flash("Subject added.", "success")
        return redirect(url_for("admin_bp.subjects"))

    all_subjects = Subject.query.order_by(Subject.subject_name).all()
    courses = Course.query.all()
    return render_template("admin/subjects.html", subjects=all_subjects, courses=courses)


@admin_bp.route("/subjects/<int:subject_id>/delete", methods=["POST"])
def subjects_delete(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    flash("Subject deleted.", "info")
    return redirect(url_for("admin_bp.subjects"))


# ---------------------------------------------------------------
# LIBRARY CATALOG (CRUD)
# ---------------------------------------------------------------

@admin_bp.route("/library", methods=["GET", "POST"])
def library():
    if request.method == "POST":
        total = request.form.get("total_copies", type=int, default=1)
        book = Book(
            title=request.form["title"].strip(),
            author=request.form.get("author", "").strip(),
            category=request.form.get("category", "").strip(),
            isbn=request.form.get("isbn", "").strip() or None,
            total_copies=total,
            available_copies=total,
        )
        db.session.add(book)
        db.session.commit()
        flash("Book added to catalog.", "success")
        return redirect(url_for("admin_bp.library"))

    books = Book.query.order_by(Book.title).all()
    return render_template("admin/library.html", books=books)


@admin_bp.route("/library/<int:book_id>/delete", methods=["POST"])
def library_delete(book_id):
    book = Book.query.get_or_404(book_id)
    if any(i.status == "issued" for i in book.issues):
        flash("Cannot delete a book with copies currently issued.", "danger")
        return redirect(url_for("admin_bp.library"))
    db.session.delete(book)
    db.session.commit()
    flash("Book removed from catalog.", "info")
    return redirect(url_for("admin_bp.library"))


# ---------------------------------------------------------------
# NOTIFICATIONS (CRUD)
# ---------------------------------------------------------------

@admin_bp.route("/notifications", methods=["GET", "POST"])
def notifications():
    if request.method == "POST":
        dept_id = request.form.get("dept_id", type=int) or None
        notif = Notification(
            title=request.form["title"].strip(),
            message=request.form["message"].strip(),
            target_role=request.form.get("target_role", "all"),
            dept_id=dept_id,
            created_by=current_user.user_id,
        )
        db.session.add(notif)
        db.session.commit()
        flash("Notification posted.", "success")
        return redirect(url_for("admin_bp.notifications"))

    all_notifications = Notification.query.order_by(Notification.created_at.desc()).all()
    departments = Department.query.order_by(Department.dept_name).all()
    return render_template(
        "admin/notifications.html",
        notifications=all_notifications,
        departments=departments,
        roles=ALL_ROLES,
    )


@admin_bp.route("/notifications/<int:notification_id>/delete", methods=["POST"])
def notifications_delete(notification_id):
    notif = Notification.query.get_or_404(notification_id)
    db.session.delete(notif)
    db.session.commit()
    flash("Notification deleted.", "info")
    return redirect(url_for("admin_bp.notifications"))
