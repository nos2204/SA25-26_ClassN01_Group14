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
    role          = db.Column(db.String(20), nullable=False, default='student')
    student_id    = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    failed_login_count = db.Column(db.Integer, default=0)
    locked_until       = db.Column(db.DateTime, nullable=True)

    student = db.relationship('StudentModel', backref='user_account', foreign_keys=[student_id])

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


class StudentModel(db.Model):
    __tablename__ = 'students'
    id              = db.Column(db.Integer, primary_key=True)
    student_code    = db.Column(db.String(20), unique=True, nullable=False)
    full_name       = db.Column(db.String(100), nullable=False)
    gender          = db.Column(db.String(10))
    email           = db.Column(db.String(120), nullable=True)
    phone           = db.Column(db.String(20), nullable=True)
    class_name      = db.Column(db.String(50), nullable=True)
    date_of_birth   = db.Column(db.Date, nullable=True)
    address         = db.Column(db.String(255), nullable=True)
    department_id   = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    gpa             = db.Column(db.Float, default=0.0)
    academic_rank   = db.Column(db.String(20), default='Yếu')
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    grades = db.relationship('GradeModel', backref='student',
                             cascade='all, delete-orphan', lazy=True)


class SubjectModel(db.Model):
    __tablename__ = 'subjects'
    id              = db.Column(db.Integer, primary_key=True)
    subject_code    = db.Column(db.String(20), unique=True, nullable=False)
    subject_name    = db.Column(db.String(100), nullable=False)
    credits         = db.Column(db.Integer, nullable=False)
    department_id   = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)

    grades = db.relationship('GradeModel', backref='subject',
                             cascade='all, delete-orphan', lazy=True)


class SemesterModel(db.Model):
    __tablename__ = 'semesters'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(50), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    is_current    = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint('name', 'academic_year', name='uq_semester_year'),
    )

    grades = db.relationship('GradeModel', backref='semester', lazy=True)

    @property
    def display_name(self):
        return f"{self.name} – {self.academic_year}"


class GradeModel(db.Model):
    __tablename__ = 'grades'
    id             = db.Column(db.Integer, primary_key=True)
    student_id     = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id     = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    semester_id    = db.Column(db.Integer, db.ForeignKey('semesters.id'), nullable=False)
    progress_grade = db.Column(db.Float, default=0.0)
    exam_grade     = db.Column(db.Float, default=0.0)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', 'semester_id',
                            name='uq_student_subject_semester'),
    )

    @property
    def final_grade(self):
        return round(self.progress_grade * 0.4 + self.exam_grade * 0.6, 2)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id          = db.Column(db.Integer, primary_key=True)
    actor       = db.Column(db.String(50), nullable=False)
    action      = db.Column(db.String(50), nullable=False)
    target      = db.Column(db.String(200), nullable=True)
    detail      = db.Column(db.Text, nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)