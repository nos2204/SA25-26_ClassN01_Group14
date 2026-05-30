# business/student_service.py
import pandas as pd
from persistence.models import db, StudentModel, GradeModel

class StudentService:
    @staticmethod
    def calculate_student_gpa(student_id):
        grades = GradeModel.query.filter_by(student_id=student_id).all()
        if not grades: return 0.0
        
        total_points = 0.0
        total_credits = 0
        for g in grades:
            # Quy đổi điểm: Quá trình * 0.4 + Thi * 0.6
            final_10 = (g.progress_grade * 0.4) + (g.exam_grade * 0.6)
            total_points += final_10 * g.subject.credits
            total_credits += g.subject.credits
        return round(total_points / total_credits, 2) if total_credits > 0 else 0.0

    @staticmethod
    def classify_academic(gpa):
        if gpa >= 8.5: return "Giỏi"
        elif gpa >= 7.0: return "Khá"
        elif gpa >= 5.5: return "Trung bình"
        return "Yếu"

    @staticmethod
    def update_student_stats(student_id):
        student = StudentModel.query.get(student_id)
        if student:
            student.gpa = StudentService.calculate_student_gpa(student_id)
            student.academic_rank = StudentService.classify_academic(student.gpa)
            db.session.commit()

    @staticmethod
    def export_students_to_excel(file_path):
        students = StudentModel.query.all()
        data = []
        for s in students:
            data.append({
                "MSSV": s.student_code,
                "Họ và Tên": s.full_name,
                "Giới tính": s.gender,
                "Điểm GPA": s.gpa,
                "Xếp loại học lực": s.academic_rank
            })
        df = pd.DataFrame(data)
        df.to_excel(file_path, index=False)