"""
Run once after init_db.py to create one demo login for each of the 6
roles, plus a bit of sample data so the dashboards have something to show.

Usage:
    python seed_data.py
"""
from datetime import date, time

from datetime import datetime, timedelta

from app import create_app
from models import (
    db, Role, Department, Course, Subject, User,
    Student, Faculty, Timetable, Fee, Attendance, Marks, Result, Notification,
    Book, BookIssue, LeaveApplication, Complaint,
)

app = create_app()

with app.app_context():
    dept = Department.query.filter_by(dept_code="CSE").first()
    course = Course.query.filter_by(course_code="BTCSE").first()
    subject1 = Subject.query.filter_by(subject_code="CS201").first()
    subject2 = Subject.query.filter_by(subject_code="CS202").first()

    def get_role(name):
        return Role.query.filter_by(role_name=name).first()

    def create_user(username, email, full_name, role_name, dept_id=None, password="Passw0rd!"):
        existing = User.query.filter_by(username=username).first()
        if existing:
            return existing
        u = User(
            username=username, email=email, full_name=full_name,
            role_id=get_role(role_name).role_id, dept_id=dept_id,
        )
        u.set_password(password)
        db.session.add(u)
        db.session.flush()
        return u

    # --- Admin ---
    admin_user = create_user("admin", "admin@college.edu", "System Administrator", "admin")

    # --- Principal ---
    principal_user = create_user("principal", "principal@college.edu", "Dr. Kavitha Rajan", "principal")

    # --- Office staff ---
    office_user = create_user("office1", "office1@college.edu", "Ramesh Kumar", "office_staff")

    # --- HOD ---
    hod_user = create_user("hod_cse", "hod.cse@college.edu", "Dr. Anitha Sharma", "hod", dept_id=dept.dept_id)

    # --- Faculty ---
    faculty_user = create_user("faculty1", "faculty1@college.edu", "Prof. Suresh Babu", "faculty", dept_id=dept.dept_id)
    if not Faculty.query.filter_by(user_id=faculty_user.user_id).first():
        faculty = Faculty(
            user_id=faculty_user.user_id, employee_code="EMP001",
            dept_id=dept.dept_id, designation="Assistant Professor", date_joined=date(2020, 6, 1),
        )
        db.session.add(faculty)
        db.session.flush()
    else:
        faculty = Faculty.query.filter_by(user_id=faculty_user.user_id).first()

    # --- Student ---
    student_user = create_user("student1", "student1@college.edu", "Arjun Mehta", "student", dept_id=dept.dept_id)
    if not Student.query.filter_by(user_id=student_user.user_id).first():
        student = Student(
            user_id=student_user.user_id, roll_no="CSE2023001", course_id=course.course_id,
            current_semester=3, admission_year=2023, guardian_name="Rajesh Mehta",
            guardian_phone="9876543210", address="12 MG Road, Chennai",
        )
        db.session.add(student)
        db.session.flush()
    else:
        student = Student.query.filter_by(user_id=student_user.user_id).first()

    db.session.commit()

    # --- Timetable ---
    if not Timetable.query.filter_by(faculty_id=faculty.faculty_id).first():
        db.session.add_all([
            Timetable(course_id=course.course_id, semester=3, subject_id=subject1.subject_id,
                      faculty_id=faculty.faculty_id, day_of_week="Mon",
                      start_time=time(9, 0), end_time=time(10, 0), room_no="A101"),
            Timetable(course_id=course.course_id, semester=3, subject_id=subject2.subject_id,
                      faculty_id=faculty.faculty_id, day_of_week="Wed",
                      start_time=time(11, 0), end_time=time(12, 0), room_no="A101"),
        ])

    # --- Fees ---
    if not Fee.query.filter_by(student_id=student.student_id).first():
        db.session.add(Fee(
            student_id=student.student_id, semester=3, fee_type="tuition",
            amount_due=50000, amount_paid=0, due_date=date(2026, 9, 1), status="pending",
        ))

    # --- Attendance sample ---
    if not Attendance.query.filter_by(student_id=student.student_id).first():
        db.session.add_all([
            Attendance(student_id=student.student_id, subject_id=subject1.subject_id,
                       faculty_id=faculty.faculty_id, attendance_date=date(2026, 7, 1), status="present"),
            Attendance(student_id=student.student_id, subject_id=subject1.subject_id,
                       faculty_id=faculty.faculty_id, attendance_date=date(2026, 7, 3), status="absent"),
        ])

    # --- Marks sample ---
    if not Marks.query.filter_by(student_id=student.student_id).first():
        db.session.add(Marks(
            student_id=student.student_id, subject_id=subject1.subject_id,
            faculty_id=faculty.faculty_id, exam_type="internal1",
            marks_obtained=42, max_marks=50,
        ))

    # --- Results sample (a previously-completed, published semester) ---
    if not Result.query.filter_by(student_id=student.student_id).first():
        db.session.add(Result(
            student_id=student.student_id, semester=2,
            sgpa=8.4, cgpa=8.4, published=True,
        ))

    # --- Notification ---
    if not Notification.query.first():
        db.session.add(Notification(
            title="Welcome to the new semester",
            message="Classes for Semester 3 begin Monday. Check your timetable.",
            target_role="all", created_by=admin_user.user_id,
        ))

    db.session.commit()

    # --- Library catalog + a sample issue ---
    if not Book.query.first():
        book1 = Book(
            title="Introduction to Algorithms", author="Thomas H. Cormen",
            category="Computer Science", isbn="978-0262046305",
            total_copies=3, available_copies=2,
        )
        book2 = Book(
            title="Clean Code", author="Robert C. Martin",
            category="Software Engineering", isbn="978-0132350884",
            total_copies=2, available_copies=2,
        )
        db.session.add_all([book1, book2])
        db.session.flush()

        db.session.add(BookIssue(
            book_id=book1.book_id, student_id=student.student_id,
            issued_at=datetime.utcnow() - timedelta(days=3),
            due_date=(datetime.utcnow() + timedelta(days=11)).date(),
            status="issued",
        ))

    # --- Leave application samples ---
    if not LeaveApplication.query.first():
        db.session.add(LeaveApplication(
            applicant_type="student", student_id=student.student_id,
            leave_type="medical", from_date=date(2026, 9, 20), to_date=date(2026, 9, 22),
            reason="Fever and doctor-advised rest.",
        ))
        db.session.add(LeaveApplication(
            applicant_type="faculty", faculty_id=faculty.faculty_id,
            leave_type="academic", from_date=date(2026, 10, 5), to_date=date(2026, 10, 7),
            reason="Attending a research conference in Bengaluru.",
        ))

    # --- Complaint sample ---
    if not Complaint.query.first():
        db.session.add(Complaint(
            student_id=student.student_id,
            subject="Hostel water supply irregular",
            description="Water supply in Block C has been irregular for the past week, mostly in the mornings.",
            status="open",
        ))

    db.session.commit()

    print("Seed complete. Demo logins (password: Passw0rd! unless noted):")
    print("  admin       / admin      -> Admin@123 (see below)")
    print("  student1    / student  -> Passw0rd!")
    print("  faculty1    / faculty  -> Passw0rd!")
    print("  hod_cse     / hod      -> Passw0rd!")
    print("  principal   / principal-> Passw0rd!")
    print("  office1     / office_staff -> Passw0rd!")

    admin_user.set_password("Admin@123")
    db.session.commit()
