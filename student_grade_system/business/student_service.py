# business/student_service.py
import pandas as pd
from persistence.models import db, StudentModel, GradeModel, SubjectModel


class StudentService:

    # ------------------------------------------------------------------ #
    #  GPA & Xếp loại                                                     #
    # ------------------------------------------------------------------ #
    @staticmethod
    def calculate_student_gpa(student_id):
        grades = GradeModel.query.filter_by(student_id=student_id).all()
        if not grades:
            return 0.0
        total_points  = 0.0
        total_credits = 0
        for g in grades:
            final_10       = (g.progress_grade * 0.4) + (g.exam_grade * 0.6)
            total_points  += final_10 * g.subject.credits
            total_credits += g.subject.credits
        return round(total_points / total_credits, 2) if total_credits > 0 else 0.0

    @staticmethod
    def classify_academic(gpa):
        if gpa >= 8.5: return 'Giỏi'
        if gpa >= 7.0: return 'Khá'
        if gpa >= 5.5: return 'Trung bình'
        return 'Yếu'

    @staticmethod
    def update_student_stats(student_id):
        student = StudentModel.query.get(student_id)
        if student:
            student.gpa          = StudentService.calculate_student_gpa(student_id)
            student.academic_rank = StudentService.classify_academic(student.gpa)
            db.session.commit()

    # ------------------------------------------------------------------ #
    #  Tìm kiếm & lọc                                                     #
    # ------------------------------------------------------------------ #
    @staticmethod
    def search_students(keyword='', gender='', rank='', page=1, per_page=15):
        """Trả về (danh_sách_sv, tổng_trang, tổng_bản_ghi)"""
        query = StudentModel.query
        if keyword:
            like = f'%{keyword}%'
            query = query.filter(
                db.or_(
                    StudentModel.full_name.ilike(like),
                    StudentModel.student_code.ilike(like),
                    StudentModel.class_name.ilike(like),
                )
            )
        if gender:
            query = query.filter_by(gender=gender)
        if rank:
            query = query.filter_by(academic_rank=rank)

        total    = query.count()
        students = query.order_by(StudentModel.full_name).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return students.items, students.pages, total

    # ------------------------------------------------------------------ #
    #  Thống kê dashboard                                                 #
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_dashboard_stats():
        total  = StudentModel.query.count()
        gioi   = StudentModel.query.filter_by(academic_rank='Giỏi').count()
        kha    = StudentModel.query.filter_by(academic_rank='Khá').count()
        tb     = StudentModel.query.filter_by(academic_rank='Trung bình').count()
        yeu    = StudentModel.query.filter_by(academic_rank='Yếu').count()
        nam    = StudentModel.query.filter_by(gender='Nam').count()
        nu     = StudentModel.query.filter_by(gender='Nữ').count()

        # Top 5 GPA cao nhất
        top5   = (StudentModel.query
                  .filter(StudentModel.gpa > 0)
                  .order_by(StudentModel.gpa.desc())
                  .limit(5).all())

        return dict(total=total, gioi=gioi, kha=kha, tb=tb, yeu=yeu,
                    nam=nam, nu=nu, top5=top5)

    # ------------------------------------------------------------------ #
    #  Nhập / cập nhật điểm                                               #
    # ------------------------------------------------------------------ #
    @staticmethod
    def upsert_grade(student_id, subject_id, progress_grade, exam_grade):
        grade = GradeModel.query.filter_by(
            student_id=student_id, subject_id=subject_id
        ).first()
        if grade:
            grade.progress_grade = progress_grade
            grade.exam_grade     = exam_grade
        else:
            grade = GradeModel(
                student_id=student_id, subject_id=subject_id,
                progress_grade=progress_grade, exam_grade=exam_grade
            )
            db.session.add(grade)
        db.session.commit()
        StudentService.update_student_stats(student_id)

    # ------------------------------------------------------------------ #
    #  Xuất báo cáo Excel                                                 #
    # ------------------------------------------------------------------ #
    @staticmethod
    def export_students_to_excel(file_path):
        students = StudentModel.query.order_by(StudentModel.student_code).all()
        rows = []
        for s in students:
            rows.append({
                'MSSV'           : s.student_code,
                'Họ và Tên'     : s.full_name,
                'Giới tính'     : s.gender,
                'Lớp'           : s.class_name or '',
                'Email'          : s.email or '',
                'Điểm GPA'      : s.gpa,
                'Xếp loại'      : s.academic_rank,
            })
        df = pd.DataFrame(rows)
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Danh sách SV')
            ws = writer.sheets['Danh sách SV']
            # Tự động giãn cột
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col) + 4
                ws.column_dimensions[col[0].column_letter].width = min(max_len, 40)