from flask import Flask, render_template
from flask_login import LoginManager

from config import Config
from models import db, User
from security import generate_csrf_token

from auth import auth_bp
from blueprints.student import student_bp
from blueprints.faculty import faculty_bp
from blueprints.hod import hod_bp
from blueprints.principal import principal_bp
from blueprints.office import office_bp
from blueprints.admin import admin_bp
from blueprints.assignments import assignments_bp
from blueprints.certificates import certificates_bp
from blueprints.placements import placements_bp
from blueprints.events import events_bp
from blueprints.audit import audit_bp

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(hod_bp)
    app.register_blueprint(principal_bp)
    app.register_blueprint(office_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(assignments_bp)
    app.register_blueprint(certificates_bp)
    app.register_blueprint(placements_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(audit_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.context_processor
    def inject_globals():
        from datetime import datetime
        return {
            "current_year": datetime.utcnow().year,
            "csrf_token": generate_csrf_token,
        }

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
