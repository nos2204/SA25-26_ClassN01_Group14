# student_grade_system/tests/test_services.py
import unittest
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app import create_app
from persistence.models import db, StudentModel, SubjectModel, SemesterModel, GradeModel
from business.student_service import StudentService


class TestStudentService(unittest.TestCase):

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test_secret_key',
            'WTF_CSRF_ENABLED': False
        })
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_score_to_gpa4(self):
        self.assertEqual(StudentService.score_to_gpa4(9.0), 4.0)
        self.assertEqual(StudentService.score_to_gpa4(8.5), 4.0)
        self.assertEqual(StudentService.score_to_gpa4(7.5), 3.0)
        self.assertEqual(StudentService.score_to_gpa4(6.0), 2.0)
        self.assertEqual(StudentService.score_to_gpa4(4.5), 1.0)
        self.assertEqual(StudentService.score_to_gpa4(3.0), 0.0)

    def test_classify_academic(self):
        self.assertEqual(StudentService.classify_academic(3.8), 'Xuất sắc')
        self.assertEqual(StudentService.classify_academic(3.4), 'Giỏi')
        self.assertEqual(StudentService.classify_academic(2.8), 'Khá')
        self.assertEqual(StudentService.classify_academic(2.2), 'Trung bình')
        self.assertEqual(StudentService.classify_academic(1.5), 'Yếu')
        self.assertEqual(StudentService.classify_academic(0.5), 'Kém')

    def test_calculate_student_gpa(self):
        sem = SemesterModel.query.first()
        if not sem:
            sem = SemesterModel(name='Học kỳ 1', academic_year='2024-2025', is_current=True)
            db.session.add(sem)
            db.session.flush()

        student = StudentModel(student_code='SV999', full_name='Nguyễn Văn Test')
        subj1 = SubjectModel(subject_code='MATH101', subject_name='Toán Cao Cấp', credits=3)
        subj2 = SubjectModel(subject_code='PROG101', subject_name='Lập Trình Python', credits=4)
        db.session.add_all([student, subj1, subj2])
        db.session.flush()

        g1 = GradeModel(student_id=student.id, subject_id=subj1.id, semester_id=sem.id, progress_grade=8.5, exam_grade=8.5)
        g2 = GradeModel(student_id=student.id, subject_id=subj2.id, semester_id=sem.id, progress_grade=7.0, exam_grade=7.0)
        db.session.add_all([g1, g2])
        db.session.commit()

        gpa = StudentService.calculate_student_gpa(student.id)
        self.assertEqual(gpa, 3.43)


if __name__ == '__main__':
    unittest.main()
