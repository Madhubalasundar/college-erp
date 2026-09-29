"""
Creates the SQLite database file and all tables, then inserts the base
reference data (departments, courses, subjects) — the SQLite equivalent
of running database/schema.sql against MySQL.

Safe to run multiple times: it only inserts reference rows if the tables
are empty.

Usage:
    python init_db.py
"""
from app import create_app
from models import db, Department, Course, Subject, Role, ALL_ROLES

app = create_app()

with app.app_context():
    db.create_all()
    print(f"Tables created in: {app.config['SQLALCHEMY_DATABASE_URI']}")

    if Role.query.count() == 0:
        db.session.add_all([Role(role_name=r) for r in ALL_ROLES])
        db.session.commit()
        print("Roles inserted:", ", ".join(ALL_ROLES))
    else:
        print("Roles already present — skipped.")

    if Department.query.count() == 0:
        cse = Department(dept_name="Computer Science", dept_code="CSE")
        ece = Department(dept_name="Electronics & Communication", dept_code="ECE")
        mech = Department(dept_name="Mechanical Engineering", dept_code="MECH")
        db.session.add_all([cse, ece, mech])
        db.session.flush()  # so dept_id is populated before we reference it

        btcse = Course(course_name="B.Tech Computer Science", course_code="BTCSE", dept_id=cse.dept_id, duration_years=4)
        btece = Course(course_name="B.Tech Electronics", course_code="BTECE", dept_id=ece.dept_id, duration_years=4)
        db.session.add_all([btcse, btece])
        db.session.flush()

        db.session.add_all([
            Subject(subject_name="Data Structures", subject_code="CS201", course_id=btcse.course_id, semester=3, credits=4),
            Subject(subject_name="Database Systems", subject_code="CS202", course_id=btcse.course_id, semester=3, credits=4),
            Subject(subject_name="Operating Systems", subject_code="CS301", course_id=btcse.course_id, semester=5, credits=4),
        ])

        db.session.commit()
        print("Reference data (departments, courses, subjects) inserted.")
    else:
        print("Reference data already present — skipped.")

    print("Done. Now run: python seed_data.py")
