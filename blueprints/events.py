from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from models import db, Event

events_bp = Blueprint("events", __name__, url_prefix="/events")


@events_bp.before_request
def _guard():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.student_login"))


@events_bp.route("/")
@login_required
def index():
    upcoming = Event.query.filter(
        Event.start_date >= datetime.utcnow()
    ).order_by(Event.start_date).all()
    past = Event.query.filter(
        Event.start_date < datetime.utcnow()
    ).order_by(Event.start_date.desc()).limit(20).all()
    return render_template("events/index.html", upcoming=upcoming, past=past)


@events_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if current_user.role_name not in ("admin", "principal", "hod", "office_staff"):
        flash("You do not have permission to create events.", "danger")
        return redirect(url_for("events.index"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        event_type = request.form.get("event_type")
        venue = request.form.get("venue", "").strip()
        start_str = request.form.get("start_date")
        end_str = request.form.get("end_date")
        target_role = request.form.get("target_role", "all")
        dept_id = request.form.get("dept_id", type=int) or None

        if not title or not event_type or not start_str:
            flash("Title, type, and start date are required.", "danger")
            return redirect(url_for("events.create"))

        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%dT%H:%M")
            end_date = datetime.strptime(end_str, "%Y-%m-%dT%H:%M") if end_str else None
        except ValueError:
            flash("Invalid date format.", "danger")
            return redirect(url_for("events.create"))

        event = Event(
            title=title,
            description=description,
            event_type=event_type,
            venue=venue,
            start_date=start_date,
            end_date=end_date,
            target_role=target_role,
            dept_id=dept_id,
            created_by=current_user.user_id,
        )
        db.session.add(event)
        db.session.commit()

        from models import AuditLog
        db.session.add(AuditLog(
            user_id=current_user.user_id,
            action="CREATE",
            module="events",
            details=f"Created event: {title}",
        ))
        db.session.commit()

        flash("Event created.", "success")
        return redirect(url_for("events.index"))

    return render_template("events/create.html")
