from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

ROLE_STUDENT = "student"
ROLE_FACULTY = "faculty"
ROLE_HOD = "hod"
ROLE_PRINCIPAL = "principal"
ROLE_OFFICE_STAFF = "office_staff"
ROLE_ADMIN = "admin"

ALL_ROLES = [ROLE_STUDENT, ROLE_FACULTY, ROLE_HOD, ROLE_PRINCIPAL, ROLE_OFFICE_STAFF, ROLE_ADMIN]


class Role(db.Model):
    __tablename__ = "roles"
    role_id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(30), unique=True, nullable=False)
    users = db.relationship("User", backref="role", lazy=True)


class Department(db.Model):
    __tablename__ = "departments"
    dept_id = db.Column(db.Integer, primary_key=True)
    dept_name = db.Column(db.String(120), nullable=False)
    dept_code = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    courses = db.relationship("Course", backref="department", lazy=True)


class Course(db.Model):
    __tablename__ = "courses"
    course_id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(120), nullable=False)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    dept_id = db.Column(db.Integer, db.ForeignKey("departments.dept_id"), nullable=False)
    duration_years = db.Column(db.Integer, default=4)

    subjects = db.relationship("Subject", backref="course", lazy=True)
    students = db.relationship("Student", backref="course", lazy=True)


class Subject(db.Model):
    __tablename__ = "subjects"
    subject_id = db.Column(db.Integer, primary_key=True)
    subject_name = db.Column(db.String(120), nullable=False)
    subject_code = db.Column(db.String(20), unique=True, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.course_id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    credits = db.Column(db.Integer, default=3)


class User(db.Model, UserMixin):
    __tablename__ = "users"
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.role_id"), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    dept_id = db.Column(db.Integer, db.ForeignKey("departments.dept_id"), nullable=True)
    is_active_flag = db.Column("is_active", db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student_profile = db.relationship("Student", backref="user", uselist=False)
    faculty_profile = db.relationship("Faculty", backref="user", uselist=False)
    department = db.relationship("Department", foreign_keys=[dept_id])

    def get_id(self):
        return str(self.user_id)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def role_name(self):
        return self.role.role_name if self.role else None


class Student(db.Model):
    __tablename__ = "students"
    student_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), unique=True, nullable=False)
    roll_no = db.Column(db.String(30), unique=True, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.course_id"), nullable=False)
    current_semester = db.Column(db.Integer, default=1)
    admission_year = db.Column(db.Integer, nullable=False)
    guardian_name = db.Column(db.String(120))
    guardian_phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    profile_photo = db.Column(db.String(255))

    attendance_records = db.relationship("Attendance", backref="student", lazy=True)
    marks_records = db.relationship("Marks", backref="student", lazy=True)
    fee_records = db.relationship("Fee", backref="student", lazy=True)


class Faculty(db.Model):
    __tablename__ = "faculty"
    faculty_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), unique=True, nullable=False)
    employee_code = db.Column(db.String(30), unique=True, nullable=False)
    dept_id = db.Column(db.Integer, db.ForeignKey("departments.dept_id"), nullable=False)
    designation = db.Column(db.String(80))
    date_joined = db.Column(db.Date)
    # Profile fields
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10))
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    emergency_contact = db.Column(db.String(20))
    qualification = db.Column(db.String(200))
    specialization = db.Column(db.String(200))
    experience_years = db.Column(db.Integer, default=0)
    profile_photo = db.Column(db.String(255))

    department = db.relationship("Department", foreign_keys=[dept_id])


class Attendance(db.Model):
    __tablename__ = "attendance"
    attendance_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.faculty_id"), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum("present", "absent", "late", name="attendance_status"), default="present")
    remarks = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subject = db.relationship("Subject")

    __table_args__ = (db.UniqueConstraint("student_id", "subject_id", "attendance_date", name="uq_attendance"),)


class Marks(db.Model):
    __tablename__ = "marks"
    marks_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.faculty_id"), nullable=False)
    exam_type = db.Column(
        db.Enum("internal1", "internal2", "internal3", "semester", name="exam_type_enum"),
        nullable=False,
    )
    marks_obtained = db.Column(db.Numeric(5, 2), nullable=False)
    max_marks = db.Column(db.Numeric(5, 2), default=100)
    graded_at = db.Column(db.DateTime, default=datetime.utcnow)

    subject = db.relationship("Subject")

    __table_args__ = (db.UniqueConstraint("student_id", "subject_id", "exam_type", name="uq_marks"),)


class Result(db.Model):
    __tablename__ = "results"
    result_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    sgpa = db.Column(db.Numeric(4, 2), nullable=True)
    cgpa = db.Column(db.Numeric(4, 2), nullable=True)
    published = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (db.UniqueConstraint("student_id", "semester", name="uq_result"),)


class Fee(db.Model):
    __tablename__ = "fees"
    fee_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    fee_type = db.Column(db.String(60), default="tuition")
    amount_due = db.Column(db.Numeric(10, 2), nullable=False)
    amount_paid = db.Column(db.Numeric(10, 2), default=0)
    due_date = db.Column(db.Date)
    status = db.Column(db.Enum("pending", "partial", "paid", name="fee_status"), default="pending")
    receipt_no = db.Column(db.String(40), unique=True)
    paid_at = db.Column(db.DateTime, nullable=True)


class Timetable(db.Model):
    __tablename__ = "timetable"
    timetable_id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.course_id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.faculty_id"), nullable=False)
    day_of_week = db.Column(db.Enum("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", name="dow_enum"), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    room_no = db.Column(db.String(20))

    subject = db.relationship("Subject")
    faculty = db.relationship("Faculty")


class Notification(db.Model):
    __tablename__ = "notifications"
    notification_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    target_role = db.Column(db.String(30), default="all")
    dept_id = db.Column(db.Integer, db.ForeignKey("departments.dept_id"), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    department = db.relationship("Department", foreign_keys=[dept_id])
    creator = db.relationship("User", foreign_keys=[created_by])


class LeaveApplication(db.Model):
    __tablename__ = "leave_applications"
    leave_id = db.Column(db.Integer, primary_key=True)
    applicant_type = db.Column(db.Enum("student", "faculty", name="leave_applicant_type"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"), nullable=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.faculty_id"), nullable=True)
    leave_type = db.Column(db.String(40), default="general")
    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum("pending", "approved", "rejected", name="leave_status"), default="pending")
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    decided_by = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)
    decided_at = db.Column(db.DateTime, nullable=True)
    decision_remarks = db.Column(db.String(255))

    student = db.relationship("Student", foreign_keys=[student_id])
    faculty = db.relationship("Faculty", foreign_keys=[faculty_id])
    decider = db.relationship("User", foreign_keys=[decided_by])


class Book(db.Model):
    __tablename__ = "books"
    book_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    author = db.Column(db.String(150))
    category = db.Column(db.String(80))
    isbn = db.Column(db.String(30), unique=True, nullable=True)
    total_copies = db.Column(db.Integer, default=1)
    available_copies = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    issues = db.relationship("BookIssue", backref="book", lazy=True)


class BookIssue(db.Model):
    __tablename__ = "book_issues"
    issue_id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.book_id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"), nullable=False)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=False)
    returned_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.Enum("issued", "returned", "overdue", name="issue_status"), default="issued")

    student = db.relationship("Student", foreign_keys=[student_id])


class Complaint(db.Model):
    __tablename__ = "complaints"
    complaint_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum("open", "in_progress", "resolved", name="complaint_status"), default="open")
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_notes = db.Column(db.Text)

    student = db.relationship("Student", foreign_keys=[student_id])


# ---------------------------------------------------------------
# NEW MODULES
# ---------------------------------------------------------------


class Assignment(db.Model):
    __tablename__ = "assignments"
    assignment_id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.faculty_id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    max_marks = db.Column(db.Numeric(5, 2), default=100)
    due_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subject = db.relationship("Subject")
    faculty = db.relationship("Faculty")
    submissions = db.relationship("AssignmentSubmission", backref="assignment", lazy=True)


class AssignmentSubmission(db.Model):
    __tablename__ = "assignment_submissions"
    submission_id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.assignment_id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_name = db.Column(db.String(255))
    marks_obtained = db.Column(db.Numeric(5, 2), nullable=True)
    feedback = db.Column(db.Text)
    status = db.Column(db.Enum("submitted", "graded", "late", name="submission_status"), default="submitted")

    student = db.relationship("Student", foreign_keys=[student_id])


class Certificate(db.Model):
    __tablename__ = "certificates"
    certificate_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"), nullable=False)
    certificate_type = db.Column(db.Enum(
        "bonafide", "transfer", "conduct", "course_completion", "other",
        name="certificate_type_enum"
    ), nullable=False)
    purpose = db.Column(db.String(255))
    status = db.Column(db.Enum(
        "requested", "under_review", "approved", "rejected", "generated", "delivered",
        name="certificate_status"
    ), default="requested")
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)
    remarks = db.Column(db.Text)

    student = db.relationship("Student", foreign_keys=[student_id])
    resolver = db.relationship("User", foreign_keys=[resolved_by])


class Placement(db.Model):
    __tablename__ = "placements"
    placement_id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    eligibility_criteria = db.Column(db.Text)
    package_ctc = db.Column(db.String(50))
    application_deadline = db.Column(db.Date, nullable=False)
    interview_date = db.Column(db.Date, nullable=True)
    venue = db.Column(db.String(200))
    status = db.Column(db.Enum("open", "closed", "completed", name="placement_status"), default="open")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)

    creator = db.relationship("User", foreign_keys=[created_by])
    applications = db.relationship("PlacementApplication", backref="placement", lazy=True)


class PlacementApplication(db.Model):
    __tablename__ = "placement_applications"
    application_id = db.Column(db.Integer, primary_key=True)
    placement_id = db.Column(db.Integer, db.ForeignKey("placements.placement_id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"), nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum("applied", "shortlisted", "interviewed", "selected", "rejected", name="placement_app_status"), default="applied")
    remarks = db.Column(db.Text)

    student = db.relationship("Student", foreign_keys=[student_id])


class Event(db.Model):
    __tablename__ = "events"
    event_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_type = db.Column(db.Enum("academic", "cultural", "sports", "seminar", "workshop", "holiday", "exam", name="event_type_enum"), nullable=False)
    venue = db.Column(db.String(200))
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    target_role = db.Column(db.String(30), default="all")
    dept_id = db.Column(db.Integer, db.ForeignKey("departments.dept_id"), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    department = db.relationship("Department", foreign_keys=[dept_id])
    creator = db.relationship("User", foreign_keys=[created_by])


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    module = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", foreign_keys=[user_id])


class HostelBlock(db.Model):
    __tablename__ = "hostel_blocks"
    block_id = db.Column(db.Integer, primary_key=True)
    block_name = db.Column(db.String(100), nullable=False)
    block_type = db.Column(db.Enum("boys", "girls", "staff", name="hostel_block_type"), nullable=False)
    total_rooms = db.Column(db.Integer, default=0)
    warden_name = db.Column(db.String(120))

    rooms = db.relationship("HostelRoom", backref="block", lazy=True)


class HostelRoom(db.Model):
    __tablename__ = "hostel_rooms"
    room_id = db.Column(db.Integer, primary_key=True)
    block_id = db.Column(db.Integer, db.ForeignKey("hostel_blocks.block_id"), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)
    room_type = db.Column(db.Enum("single", "double", "triple", name="room_type_enum"), default="double")
    capacity = db.Column(db.Integer, default=2)
    occupied = db.Column(db.Integer, default=0)
    fee_per_semester = db.Column(db.Numeric(10, 2), default=0)

    allocations = db.relationship("HostelAllocation", backref="room", lazy=True)


class HostelAllocation(db.Model):
    __tablename__ = "hostel_allocations"
    allocation_id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("hostel_rooms.room_id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"), nullable=False)
    allocated_at = db.Column(db.DateTime, default=datetime.utcnow)
    vacated_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.Enum("active", "vacated", name="hostel_alloc_status"), default="active")

    student = db.relationship("Student", foreign_keys=[student_id])


class TransportRoute(db.Model):
    __tablename__ = "transport_routes"
    route_id = db.Column(db.Integer, primary_key=True)
    route_name = db.Column(db.String(150), nullable=False)
    bus_number = db.Column(db.String(30), nullable=False)
    driver_name = db.Column(db.String(120))
    driver_phone = db.Column(db.String(20))
    start_point = db.Column(db.String(200))
    end_point = db.Column(db.String(200))
    total_stops = db.Column(db.Integer, default=0)
    fee_per_semester = db.Column(db.Numeric(10, 2), default=0)

    stops = db.relationship("TransportStop", backref="route", lazy=True)
    allocations = db.relationship("TransportAllocation", backref="route", lazy=True)


class TransportStop(db.Model):
    __tablename__ = "transport_stops"
    stop_id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey("transport_routes.route_id"), nullable=False)
    stop_name = db.Column(db.String(150), nullable=False)
    stop_order = db.Column(db.Integer, nullable=False)
    pickup_time = db.Column(db.Time)
    drop_time = db.Column(db.Time)


class TransportAllocation(db.Model):
    __tablename__ = "transport_allocations"
    transport_allocation_id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey("transport_routes.route_id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.student_id"), nullable=False)
    stop_id = db.Column(db.Integer, db.ForeignKey("transport_stops.stop_id"), nullable=True)
    allocated_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum("active", "cancelled", name="transport_alloc_status"), default="active")

    student = db.relationship("Student", foreign_keys=[student_id])
    stop = db.relationship("TransportStop", foreign_keys=[stop_id])


# ---------------------------------------------------------------
# FACULTY PROFILE EXTENSIONS
# ---------------------------------------------------------------


class FacultyDocument(db.Model):
    __tablename__ = "faculty_documents"
    document_id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.faculty_id"), nullable=False)
    document_type = db.Column(db.Enum(
        "qualification", "experience", "appointment", "id_proof", "other",
        name="faculty_doc_type_enum"
    ), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(255))

    faculty = db.relationship("Faculty", foreign_keys=[faculty_id])


class FacultyAttendance(db.Model):
    __tablename__ = "faculty_attendance"
    attendance_id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.faculty_id"), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum("present", "absent", "leave", name="faculty_att_status"), default="present")
    check_in = db.Column(db.Time, nullable=True)
    check_out = db.Column(db.Time, nullable=True)
    remarks = db.Column(db.String(255))

    __table_args__ = (db.UniqueConstraint("faculty_id", "attendance_date", name="uq_faculty_att"),)
