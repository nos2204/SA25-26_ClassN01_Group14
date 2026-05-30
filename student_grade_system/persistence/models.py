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
    # 'admin' hoặc 'student'
    role          = db.Column(db.String(20), nullable=False, default='student')
    # Liên kết tùy chọn: nếu role='student' thì trỏ đến hồ sơ sinh viên
    student_id    = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('StudentModel', backref='user_account', foreign_keys=[student_id])

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class StudentModel(db.Model):
    __tablename__ = 'students'
    id            = db.Column(db.Integer, primary_key=True)
    student_code  = db.Column(db.String(20), unique=True, nullable=False)
    full_name     = db.Column(db.String(100), nullable=False)
    gender        = db.Column(db.String(10))
    # Trường mới bổ sung
    email         = db.Column(db.String(120), nullable=True)
    phone         = db.Column(db.String(20), nullable=True)
    class_name    = db.Column(db.String(50), nullable=True)   # Lớp học
    date_of_birth = db.Column(db.Date, nullable=True)
    # Tự động tính toán bởi StudentService
    gpa           = db.Column(db.Float, default=0.0)
    academic_rank = db.Column(db.String(20), default='Yếu')
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    grades = db.relationship('GradeModel', backref='student',
                             cascade='all, delete-orphan', lazy=True)


class SubjectModel(db.Model):
    __tablename__ = 'subjects'
    id            = db.Column(db.Integer, primary_key=True)
    subject_code  = db.Column(db.String(20), unique=True, nullable=False)
    subject_name  = db.Column(db.String(100), nullable=False)
    credits       = db.Column(db.Integer, nullable=False)

    grades = db.relationship('GradeModel', backref='subject',
                             cascade='all, delete-orphan', lazy=True)


class GradeModel(db.Model):
    __tablename__ = 'grades'
    id             = db.Column(db.Integer, primary_key=True)
    student_id     = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id     = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    progress_grade = db.Column(db.Float, default=0.0)   # Điểm quá trình (40%)
    exam_grade     = db.Column(db.Float, default=0.0)   # Điểm thi cuối kỳ (60%)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Ràng buộc: mỗi sinh viên chỉ có 1 dòng điểm / môn học
    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', name='uq_student_subject'),
    )