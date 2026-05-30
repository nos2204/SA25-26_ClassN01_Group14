# persistence/models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class UserModel(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'student'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class StudentModel(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_code = db.Column(db.String(20), unique=True, nullable=False) # MSSV
    full_name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10))
    gpa = db.Column(db.Float, default=0.0)
    academic_rank = db.Column(db.String(20), default="Yếu") # Tự động phân loại học lực
    grades = db.relationship('GradeModel', backref='student', cascade="all, delete-orphan", lazy=True)

class SubjectModel(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    subject_code = db.Column(db.String(20), unique=True, nullable=False)
    subject_name = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, nullable=False)

class GradeModel(db.Model):
    __tablename__ = 'grades'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    progress_grade = db.Column(db.Float, default=0.0) # Điểm thành phần quá trình (40%)
    exam_grade = db.Column(db.Float, default=0.0)     # Điểm thi cuối kỳ (60%)
    
    subject = db.relationship('SubjectModel')