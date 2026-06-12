# persistence/models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class UserModel(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default='student')  # admin / teacher / student
    student_id    = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    teacher_id    = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    failed_login_count = db.Column(db.Integer, default=0)
    locked_until       = db.Column(db.DateTime, nullable=True)

    student = db.relationship('StudentModel', backref='user_account', foreign_keys=[student_id])
    teacher = db.relationship('TeacherModel', backref='user_account', foreign_keys=[teacher_id])

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_locked(self):
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return True
        return False

    def reset_lock(self):
        self.failed_login_count = 0
        self.locked_until = None


class DepartmentModel(db.Model):
    __tablename__ = 'departments'
    id              = db.Column(db.Integer, primary_key=True)
    department_code = db.Column(db.String(20), unique=True, nullable=False)
    department_name = db.Column(db.String(100), nullable=False)

    students = db.relationship('StudentModel', backref='department', lazy=True)
    subjects = db.relationship('SubjectModel', backref='department', lazy=True)
    classes  = db.relationship('ClassModel', backref='department', lazy=True)
    teachers = db.relationship('TeacherModel', backref='department', lazy=True)


class ClassModel(db.Model):
    __tablename__ = 'classes'
    id            = db.Column(db.Integer, primary_key=True)
    class_code    = db.Column(db.String(20), unique=True, nullable=False)
    class_name    = db.Column(db.String(100), nullable=False)
    academic_year = db.Column(db.String(20), nullable=True)
    advisor_name  = db.Column(db.String(100), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)

    students = db.relationship('StudentModel', backref='class_info', lazy=True)

    @property
    def display_name(self):
        return f"{self.class_code} - {self.class_name}"


class StudentModel(db.Model):
    __tablename__ = 'students'
    id              = db.Column(db.Integer, primary_key=True)
    student_code    = db.Column(db.String(20), unique=True, nullable=False)
    full_name       = db.Column(db.String(100), nullable=False)
    gender          = db.Column(db.String(10))
    email           = db.Column(db.String(120), nullable=True)
    phone           = db.Column(db.String(20), nullable=True)
    class_name      = db.Column(db.String(50), nullable=True)  # dữ liệu cũ, vẫn giữ để không mất dữ liệu
    class_id        = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)
    date_of_birth   = db.Column(db.Date, nullable=True)
    address         = db.Column(db.String(255), nullable=True)
    department_id   = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    gpa             = db.Column(db.Float, default=0.0)
    academic_rank   = db.Column(db.String(20), default='Yếu')
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    grades = db.relationship('GradeModel', backref='student', cascade='all, delete-orphan', lazy=True)

    @property
    def display_class(self):
        if self.class_info:
            return self.class_info.display_name
        return self.class_name or ''


class TeacherModel(db.Model):
    __tablename__ = 'teachers'
    id              = db.Column(db.Integer, primary_key=True)
    teacher_code    = db.Column(db.String(20), unique=True, nullable=False)
    full_name       = db.Column(db.String(100), nullable=False)
    email           = db.Column(db.String(120), nullable=True)
    phone           = db.Column(db.String(20), nullable=True)
    department_id   = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    sections = db.relationship('CourseSectionModel', backref='teacher', lazy=True)


class SubjectModel(db.Model):
    __tablename__ = 'subjects'
    id              = db.Column(db.Integer, primary_key=True)
    subject_code    = db.Column(db.String(20), unique=True, nullable=False)
    subject_name    = db.Column(db.String(100), nullable=False)
    credits         = db.Column(db.Integer, nullable=False)
    department_id   = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)

    grades = db.relationship('GradeModel', backref='subject', cascade='all, delete-orphan', lazy=True)
    sections = db.relationship('CourseSectionModel', backref='subject', lazy=True)


class SemesterModel(db.Model):
    __tablename__ = 'semesters'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(50), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    is_current    = db.Column(db.Boolean, default=False)

    __table_args__ = (db.UniqueConstraint('name', 'academic_year', name='uq_semester_year'),)

    grades = db.relationship('GradeModel', backref='semester', lazy=True)
    sections = db.relationship('CourseSectionModel', backref='semester', lazy=True)

    @property
    def display_name(self):
        return f"{self.name} – {self.academic_year}"


class CourseSectionModel(db.Model):
    __tablename__ = 'course_sections'
    id            = db.Column(db.Integer, primary_key=True)
    section_code  = db.Column(db.String(30), unique=True, nullable=False)
    subject_id    = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    semester_id   = db.Column(db.Integer, db.ForeignKey('semesters.id'), nullable=False)
    teacher_id    = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)
    max_students  = db.Column(db.Integer, default=50)
    room          = db.Column(db.String(50), nullable=True)
    schedule      = db.Column(db.String(120), nullable=True)
    status        = db.Column(db.String(30), default='open')  # open / closed / studying / finished / locked
    grades_locked = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    enrollments = db.relationship('EnrollmentModel', backref='section', cascade='all, delete-orphan', lazy=True)

    @property
    def current_students(self):
        return len([e for e in self.enrollments if e.status == 'registered'])

    @property
    def is_full(self):
        return self.current_students >= (self.max_students or 0)


class EnrollmentModel(db.Model):
    __tablename__ = 'enrollments'
    id            = db.Column(db.Integer, primary_key=True)
    student_id    = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    section_id    = db.Column(db.Integer, db.ForeignKey('course_sections.id'), nullable=False)
    status        = db.Column(db.String(20), default='registered')
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('StudentModel', backref='enrollments')

    __table_args__ = (db.UniqueConstraint('student_id', 'section_id', name='uq_student_section'),)


class GradeModel(db.Model):
    __tablename__ = 'grades'
    id             = db.Column(db.Integer, primary_key=True)
    student_id     = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id     = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    semester_id    = db.Column(db.Integer, db.ForeignKey('semesters.id'), nullable=False)
    progress_grade = db.Column(db.Float, default=0.0)
    exam_grade     = db.Column(db.Float, default=0.0)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('student_id', 'subject_id', 'semester_id', name='uq_student_subject_semester'),)

    @property
    def final_grade(self):
        return round((self.progress_grade or 0) * 0.4 + (self.exam_grade or 0) * 0.6, 2)

    @property
    def letter_grade(self):
        score = self.final_grade
        if score >= 8.5: return 'A'
        if score >= 7.0: return 'B'
        if score >= 5.5: return 'C'
        if score >= 4.0: return 'D'
        return 'F'

    @property
    def grade_point_4(self):
        """Quy đổi sang thang điểm 4 (GPA)"""
        return {'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0, 'F': 0.0}.get(self.letter_grade, 0.0)

    @staticmethod
    def diem10_to_gpa4(score):
        """Chuyển đổi điểm thang 10 sang thang 4"""
        if score >= 8.5: return 4.0
        if score >= 7.0: return 3.0
        if score >= 5.5: return 2.0
        if score >= 4.0: return 1.0
        return 0.0

    @property
    def is_passed(self):
        return self.final_grade >= 4.0


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id          = db.Column(db.Integer, primary_key=True)
    actor       = db.Column(db.String(50), nullable=False)
    action      = db.Column(db.String(50), nullable=False)
    target      = db.Column(db.String(200), nullable=True)
    detail      = db.Column(db.Text, nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
