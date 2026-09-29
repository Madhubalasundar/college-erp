from functools import wraps
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, current_app
)
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from models import db, User, Student
from security import (
    rate_limit, record_failed_attempt, clear_failed_attempts,
    generate_csrf_token, validate_csrf_token,
)

auth_bp = Blueprint("auth", __name__)

ROLE_DASHBOARD_ENDPOINT = {
    "student": "student.dashboard",
    "faculty": "faculty.dashboard",
    "hod": "hod.dashboard",
    "principal": "principal.dashboard",
    "office_staff": "office.dashboard",
    "admin": "admin_bp.dashboard",
}


def roles_required(*roles):
    """Decorator restricting a view to one or more role names."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.role_name not in roles:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for(ROLE_DASHBOARD_ENDPOINT.get(current_user.role_name, "auth.login")))
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


@auth_bp.route("/", methods=["GET"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for(ROLE_DASHBOARD_ENDPOINT[current_user.role_name]))
    return render_template("landing.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(ROLE_DASHBOARD_ENDPOINT[current_user.role_name]))

    if request.method == "POST":
        # Validate CSRF
        if not validate_csrf_token():
            flash("Invalid form submission. Please try again.", "danger")
            return render_template("login.html", selected_role=request.form.get("role", ""), csrf_token=generate_csrf_token())

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role_selected = request.form.get("role", "")

        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if not user or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return render_template("login.html", selected_role=role_selected, csrf_token=generate_csrf_token())

        if not user.is_active_flag:
            flash("Your account has been deactivated. Contact the admin office.", "danger")
            return render_template("login.html", selected_role=role_selected, csrf_token=generate_csrf_token())

        if user.role_name != role_selected:
            flash(f"That account is not registered as {role_selected.replace('_', ' ').title()}.", "danger")
            return render_template("login.html", selected_role=role_selected, csrf_token=generate_csrf_token())

        login_user(user, remember=True)
        session.permanent = True

        from datetime import datetime
        user.last_login = datetime.utcnow()
        db.session.commit()

        flash(f"Welcome back, {user.full_name}!", "success")
        return redirect(url_for(ROLE_DASHBOARD_ENDPOINT[user.role_name]))

    role_selected = request.args.get("role", "student")
    return render_template("login.html", selected_role=role_selected, csrf_token=generate_csrf_token())


# ---------------------------------------------------------------
# Student Login (dedicated page)
# ---------------------------------------------------------------


@auth_bp.route("/student/login", methods=["GET", "POST"])
@rate_limit(max_attempts=5, window=300)
def student_login():
    """Dedicated student login page with enhanced security."""
    if current_user.is_authenticated:
        if current_user.role_name == "student":
            return redirect(url_for("student.dashboard"))
        return redirect(url_for(ROLE_DASHBOARD_ENDPOINT.get(current_user.role_name, "auth.index")))

    if request.method == "POST":
        # Validate CSRF
        if not validate_csrf_token():
            flash("Invalid form submission. Please try again.", "danger")
            return render_template("student_login.html", csrf_token=generate_csrf_token())

        student_id = request.form.get("student_id", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        # Validation
        errors = []
        if not student_id:
            errors.append("Please enter your Student ID.")
        if not password:
            errors.append("Please enter your password.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("student_login.html", csrf_token=generate_csrf_token())

        # Find user by roll_no or username
        user = (
            User.query.join(Student, User.user_id == Student.user_id)
            .filter((Student.roll_no == student_id) | (User.username == student_id))
            .first()
        )

        if not user or not user.check_password(password):
            record_failed_attempt()
            flash("Invalid Student ID or password.", "danger")
            return render_template("student_login.html", csrf_token=generate_csrf_token())

        if user.role_name != "student":
            flash("This account is not registered as a Student.", "danger")
            return render_template("student_login.html", csrf_token=generate_csrf_token())

        if not user.is_active_flag:
            flash("Your account has been deactivated. Contact the admin office.", "danger")
            return render_template("student_login.html", csrf_token=generate_csrf_token())

        # Successful login
        clear_failed_attempts()
        login_user(user, remember=remember)
        session.permanent = True

        from datetime import datetime
        user.last_login = datetime.utcnow()
        db.session.commit()

        flash(f"Welcome back, {user.full_name}!", "success")
        return redirect(url_for("student.dashboard"))

    return render_template("student_login.html", csrf_token=generate_csrf_token())


# ---------------------------------------------------------------
# Forgot Password
# ---------------------------------------------------------------


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Forgot password - step 1: verify student ID."""
    if current_user.is_authenticated:
        return redirect(url_for(ROLE_DASHBOARD_ENDPOINT.get(current_user.role_name, "auth.index")))

    if request.method == "POST":
        # Validate CSRF
        if not validate_csrf_token():
            flash("Invalid form submission. Please try again.", "danger")
            return render_template("forgot_password.html", csrf_token=generate_csrf_token())

        student_id = request.form.get("student_id", "").strip()

        if not student_id:
            flash("Please enter your Student ID.", "danger")
            return render_template("forgot_password.html", csrf_token=generate_csrf_token())

        # Find the student
        student = Student.query.filter_by(roll_no=student_id).first()

        if not student:
            # Don't reveal whether the student exists (security best practice)
            flash("If this Student ID exists, a password reset link has been generated.", "info")
            return render_template("forgot_password.html", csrf_token=generate_csrf_token())

        # Generate a time-limited reset token
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        token = serializer.dumps(student.user_id, salt="password-reset")

        # In production, this token would be sent via email
        # For this demo, redirect to the reset page
        return redirect(url_for("auth.reset_password", token=token))

    return render_template("forgot_password.html", csrf_token=generate_csrf_token())


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Reset password - step 2: set new password."""
    if current_user.is_authenticated:
        return redirect(url_for(ROLE_DASHBOARD_ENDPOINT.get(current_user.role_name, "auth.index")))

    # Validate token
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        user_id = serializer.loads(token, salt="password-reset", max_age=3600)  # 1 hour expiry
    except (BadSignature, SignatureExpired):
        flash("This password reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    user = User.query.get(user_id)
    if not user or user.role_name != "student":
        flash("Invalid password reset request.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        # Validate CSRF
        if not validate_csrf_token():
            flash("Invalid form submission. Please try again.", "danger")
            return render_template("reset_password.html", token=token, csrf_token=generate_csrf_token())

        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("reset_password.html", token=token, csrf_token=generate_csrf_token())

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html", token=token, csrf_token=generate_csrf_token())

        user.set_password(password)
        db.session.commit()

        flash("Your password has been reset. Please log in.", "success")
        return redirect(url_for("auth.student_login"))

    return render_template("reset_password.html", token=token, csrf_token=generate_csrf_token())


# ---------------------------------------------------------------
# Logout
# ---------------------------------------------------------------


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.student_login"))


# ---------------------------------------------------------------
# Change Password
# ---------------------------------------------------------------


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        # Validate CSRF
        if not validate_csrf_token():
            flash("Invalid form submission. Please try again.", "danger")
            return render_template("change_password.html", csrf_token=generate_csrf_token())

        current_pw = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")
        confirm_pw = request.form.get("confirm_password", "")

        if not current_user.check_password(current_pw):
            flash("Current password is incorrect.", "danger")
        elif len(new_pw) < 8:
            flash("New password must be at least 8 characters.", "danger")
        elif new_pw != confirm_pw:
            flash("New passwords do not match.", "danger")
        else:
            current_user.set_password(new_pw)
            db.session.commit()
            flash("Password updated successfully.", "success")
            return redirect(url_for(ROLE_DASHBOARD_ENDPOINT[current_user.role_name]))

    return render_template("change_password.html", csrf_token=generate_csrf_token())
