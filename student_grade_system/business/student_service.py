# business/student_service.py
import io
import csv
import pandas as pd
from datetime import datetime
from flask import session
from persistence.models import db, StudentModel, GradeModel, SubjectModel, SemesterModel, AuditLog


class StudentService:

    @staticmethod
    def calculate_student_gpa(student_id, semester_id=None):
        query = GradeModel.query.filter_by(student_id=student_id)
        if semester_id:
            query = query.filter_by(semester_id=semester_id)
        grades = query.all()
        if not grades:
            return 0.0
        total_points  = 0.0
        total_credits = 0
        for g in grades:
            total_points  += g.final_grade * g.subject.credits
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
            student.gpa           = StudentService.calculate_student_gpa(student_id)
            student.academic_rank = StudentService.classify_academic(student.gpa)
            db.session.commit()

    @staticmethod
    def search_students(keyword='', gender='', rank='', department_id='',
                        page=1, per_page=15):
        query = StudentModel.query
        if keyword:
            like  = f'%{keyword}%'
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
        if department_id:
            query = query.filter_by(department_id=department_id)

        total    = query.count()
        students = query.order_by(StudentModel.full_name).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return students.items, students.pages, total

    @staticmethod
    def get_dashboard_stats():
        total = StudentModel.query.count()
        gioi  = StudentModel.query.filter_by(academic_rank='Giỏi').count()
        kha   = StudentModel.query.filter_by(academic_rank='Khá').count()
        tb    = StudentModel.query.filter_by(academic_rank='Trung bình').count()
        yeu   = StudentModel.query.filter_by(academic_rank='Yếu').count()
        nam   = StudentModel.query.filter_by(gender='Nam').count()
        nu    = StudentModel.query.filter_by(gender='Nữ').count()

        top5  = (StudentModel.query
                 .filter(StudentModel.gpa > 0)
                 .order_by(StudentModel.gpa.desc())
                 .limit(5).all())

        current_sem = SemesterModel.query.filter_by(is_current=True).first()

        return dict(total=total, gioi=gioi, kha=kha, tb=tb, yeu=yeu,
                    nam=nam, nu=nu, top5=top5, current_sem=current_sem)

    @staticmethod
    def upsert_grade(student_id, subject_id, semester_id,
                     progress_grade, exam_grade, actor='system'):
        grade = GradeModel.query.filter_by(
            student_id=student_id, subject_id=subject_id,
            semester_id=semester_id
        ).first()

        subject  = SubjectModel.query.get(subject_id)
        student  = StudentModel.query.get(student_id)
        sem_name = SemesterModel.query.get(semester_id).display_name if semester_id else '?'

        if grade:
            old_detail = (f"QT={grade.progress_grade}, Thi={grade.exam_grade}")
            grade.progress_grade = progress_grade
            grade.exam_grade     = exam_grade
            grade.updated_at     = datetime.utcnow()
            action = 'update_grade'
        else:
            old_detail = 'mới'
            grade = GradeModel(
                student_id=student_id, subject_id=subject_id,
                semester_id=semester_id,
                progress_grade=progress_grade, exam_grade=exam_grade
            )
            db.session.add(grade)
            action = 'insert_grade'

        db.session.commit()
        StudentService.update_student_stats(student_id)

        log = AuditLog(
            actor=actor,
            action=action,
            target=f"SV={student.student_code} | Môn={subject.subject_code} | Kỳ={sem_name}",
            detail=f"Cũ: {old_detail} → Mới: QT={progress_grade}, Thi={exam_grade}"
        )
        db.session.add(log)
        db.session.commit()

    @staticmethod
    def import_students_from_csv(file_stream, actor='admin'):
        added   = 0
        skipped = 0
        errors  = []

        text    = io.TextIOWrapper(file_stream, encoding='utf-8-sig')
        reader  = csv.DictReader(text)

        for i, row in enumerate(reader, start=2):
            code = row.get('student_code', '').strip()
            name = row.get('full_name', '').strip()
            if not code or not name:
                errors.append(f"Dòng {i}: thiếu MSSV hoặc họ tên.")
                continue

            if StudentModel.query.filter_by(student_code=code).first():
                skipped += 1
                continue

            dob = None
            dob_str = row.get('date_of_birth', '').strip()
            if dob_str:
                try:
                    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                except ValueError:
                    errors.append(f"Dòng {i}: ngày sinh '{dob_str}' không đúng định dạng YYYY-MM-DD.")

            student = StudentModel(
                student_code  = code,
                full_name     = name,
                gender        = row.get('gender', 'Nam').strip() or 'Nam',
                email         = row.get('email', '').strip() or None,
                phone         = row.get('phone', '').strip() or None,
                class_name    = row.get('class_name', '').strip() or None,
                date_of_birth = dob,
            )
            db.session.add(student)
            added += 1

        db.session.commit()

        log = AuditLog(actor=actor, action='import_students',
                       detail=f"Thêm {added}, bỏ qua {skipped}, lỗi {len(errors)}")
        db.session.add(log)
        db.session.commit()

        return added, skipped, errors

    @staticmethod
    def import_grades_from_csv(file_stream, semester_id, actor='admin'):
        updated = 0
        errors  = []

        text   = io.TextIOWrapper(file_stream, encoding='utf-8-sig')
        reader = csv.DictReader(text)

        for i, row in enumerate(reader, start=2):
            sc   = row.get('student_code', '').strip()
            subc = row.get('subject_code', '').strip()
            try:
                pg = float(row.get('progress_grade', 0))
                eg = float(row.get('exam_grade', 0))
                assert 0 <= pg <= 10 and 0 <= eg <= 10
            except (ValueError, AssertionError):
                errors.append(f"Dòng {i}: điểm không hợp lệ.")
                continue

            student = StudentModel.query.filter_by(student_code=sc).first()
            subject = SubjectModel.query.filter_by(subject_code=subc).first()
            if not student:
                errors.append(f"Dòng {i}: không tìm thấy MSSV '{sc}'.")
                continue
            if not subject:
                errors.append(f"Dòng {i}: không tìm thấy mã môn '{subc}'.")
                continue

            StudentService.upsert_grade(student.id, subject.id, semester_id,
                                        pg, eg, actor=actor)
            updated += 1

        return updated, errors

    @staticmethod
    def export_students_to_excel(file_path, semester_id=None):
        students = StudentModel.query.order_by(StudentModel.student_code).all()
        rows = []
        for s in students:
            gpa = (StudentService.calculate_student_gpa(s.id, semester_id)
                   if semester_id else s.gpa)
            rows.append({
                'MSSV'       : s.student_code,
                'Họ và Tên' : s.full_name,
                'Giới tính' : s.gender,
                'Lớp'       : s.class_name or '',
                'Email'      : s.email or '',
                'Điểm GPA'  : gpa,
                'Xếp loại'  : StudentService.classify_academic(gpa),
            })
        df = pd.DataFrame(rows)
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Danh sách SV')
            ws = writer.sheets['Danh sách SV']
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col) + 4
                ws.column_dimensions[col[0].column_letter].width = min(max_len, 40)

    @staticmethod
    def export_transcript_pdf(student_id, semester_id=None):
        try:
            from weasyprint import HTML
        except ImportError:
            raise RuntimeError("Cần cài weasyprint: pip install weasyprint")

        student  = StudentModel.query.get_or_404(student_id)
        query    = GradeModel.query.filter_by(student_id=student_id)
        if semester_id:
            query = query.filter_by(semester_id=semester_id)
        grades   = query.all()
        sem_name = (SemesterModel.query.get(semester_id).display_name
                    if semester_id else 'Toàn khoá')
        gpa      = StudentService.calculate_student_gpa(student_id, semester_id)

        rows_html = ''
        for i, g in enumerate(grades, 1):
            rows_html += f"""
            <tr>
                <td>{i}</td>
                <td>{g.subject.subject_code}</td>
                <td>{g.subject.subject_name}</td>
                <td style="text-align:center">{g.subject.credits}</td>
                <td style="text-align:center">{g.progress_grade}</td>
                <td style="text-align:center">{g.exam_grade}</td>
                <td style="text-align:center;font-weight:bold">{g.final_grade}</td>
            </tr>"""

        html_content = f"""
        <!DOCTYPE html>
        <html lang="vi">
        <head>
          <meta charset="UTF-8">
          <style>
            body {{ font-family: Arial, sans-serif; font-size: 13px; margin: 30px; }}
            h2 {{ text-align: center; font-size: 16px; margin-bottom: 4px; }}
            .subtitle {{ text-align: center; color: #555; margin-bottom: 20px; }}
            .info {{ margin-bottom: 16px; }}
            .info span {{ margin-right: 24px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background: #212529; color: #fff; padding: 7px; }}
            td {{ border: 1px solid #ccc; padding: 6px; }}
            tr:nth-child(even) td {{ background: #f8f8f8; }}
            .gpa-row {{ margin-top: 16px; font-size: 14px; font-weight: bold; }}
            .footer {{ margin-top: 40px; text-align: right; font-size: 12px; color: #777; }}
          </style>
        </head>
        <body>
          <h2>BẢNG KẾT QUẢ HỌC TẬP</h2>
          <div class="subtitle">Hệ thống Quản lý Sinh viên — QLSV</div>
          <div class="info">
            <span><b>MSSV:</b> {student.student_code}</span>
            <span><b>Họ tên:</b> {student.full_name}</span>
            <span><b>Lớp:</b> {student.class_name or '—'}</span>
            <span><b>Học kỳ:</b> {sem_name}</span>
          </div>
          <table>
            <thead>
              <tr>
                <th>#</th><th>Mã môn</th><th>Tên môn học</th><th>TC</th>
                <th>Điểm QT</th><th>Điểm thi</th><th>Tổng kết</th>
              </tr>
            </thead>
            <tbody>{rows_html}</tbody>
          </table>
          <div class="gpa-row">GPA {sem_name}: {gpa} — {StudentService.classify_academic(gpa)}</div>
          <div class="footer">Xuất lúc {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
        </body>
        </html>
        """

        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes