"""
Layer 2 – Business Logic: StudentService
Chứa toàn bộ quy tắc nghiệp vụ, validation và điều phối gọi Persistence Layer.
Controller (Presentation) KHÔNG được truy cập trực tiếp Repository.
"""

from persistence.student_repository import StudentRepository


class StudentService:
    """
    Layer 2: Xử lý quy tắc nghiệp vụ, validation và logic tính toán.
    Phụ thuộc vào (requires) StudentRepository ở Layer 3.
    """

    def __init__(self):
        self.repo = StudentRepository()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def add_student(self, dep, student_id, name, division, gender,
                    email, dob, grade, credits):
        """Quy tắc nghiệp vụ: dep và student_id là bắt buộc."""
        if not dep or dep == "Select Major":
            raise ValueError("Vui lòng chọn ngành học.")
        if not student_id:
            raise ValueError("Mã sinh viên không được để trống.")
        if not name:
            raise ValueError("Tên sinh viên không được để trống.")
        return self.repo.create(dep, student_id, name, division, gender,
                                email, dob, grade, credits)

    def get_all_students(self):
        return self.repo.find_all()

    def get_student(self, student_id):
        student = self.repo.find_by_id(student_id)
        if not student:
            raise ValueError(f"Sinh viên với ID '{student_id}' không tồn tại.")
        return student

    def update_student(self, dep, student_id, name, division, gender,
                       email, dob, grade, credits):
        if not dep or not student_id:
            raise ValueError("Ngành học và Mã sinh viên là bắt buộc.")
        return self.repo.update(dep, student_id, name, division, gender,
                                email, dob, grade, credits)

    def delete_student(self, student_id):
        if not student_id:
            raise ValueError("Mã sinh viên không được để trống.")
        return self.repo.delete(student_id)

    def search_students(self, field, keyword):
        allowed_fields = {"Name": "Name", "DOB": "DOB", "StudentID": "StudentID"}
        if field not in allowed_fields:
            raise ValueError(f"Trường tìm kiếm không hợp lệ: {field}")
        return self.repo.search(allowed_fields[field], keyword)

    def sort_students(self, sort_option):
        sort_map = {
            "Name": "Name",
            "StudentID": "StudentID",
            "DOB": "DOB",
            "Grade": "Grade",
        }
        if sort_option not in sort_map:
            raise ValueError(f"Tùy chọn sắp xếp không hợp lệ: {sort_option}")
        return self.repo.find_all_sorted(sort_map[sort_option])

    # ── GPA & Học bổng ───────────────────────────────────────────────────────

    @staticmethod
    def convert_grade_to_gpa(grade: float) -> float:
        """Công thức chuyển đổi điểm sang GPA (thang 4)."""
        return round(grade * 0.4, 2)

    def calculate_gpa_and_scholarship(self):
        """
        Tính GPA và xác định học bổng cho toàn bộ sinh viên.
        Trả về danh sách student_id có GPA thấp (<= 2.3).
        """
        students = self.repo.find_all()
        low_gpa_students = []

        for student in students:
            try:
                grade = float(student.grade) if student.grade is not None else 0.0
            except (ValueError, TypeError):
                grade = 0.0

            gpa = self.convert_grade_to_gpa(grade)
            scholarship = "Yes" if gpa >= 3.6 else "No"

            self.repo.update_gpa_scholarship(student.student_id, gpa, scholarship)

            if gpa <= 2.3:
                low_gpa_students.append(student.student_id)

        return low_gpa_students

    def calculate_max_gpa(self, grade: float, credits: int) -> dict:
        """
        Tính GPA tối đa có thể đạt được với số tín chỉ còn lại.
        Tổng tín chỉ toàn khóa = 141 tín chỉ.
        """
        TOTAL_CREDITS = 141
        gpa_current = self.convert_grade_to_gpa(grade)
        remaining = TOTAL_CREDITS - credits

        if remaining < 0:
            raise ValueError("Số tín chỉ đã học vượt quá tổng tín chỉ toàn khóa (141).")

        gpa_max = (gpa_current * credits + 4.0 * remaining) / TOTAL_CREDITS
        gpa_max = round(gpa_max, 2)

        if gpa_max >= 3.6:
            classification = "Xuất sắc"
        elif gpa_max >= 3.2:
            classification = "Giỏi"
        elif gpa_max >= 2.5:
            classification = "Khá"
        else:
            classification = "Trung bình"

        return {"gpa_max": gpa_max, "classification": classification}

    def get_gpa_statistics(self):
        """
        Lấy dữ liệu thống kê số lượng sinh viên theo khoảng GPA.
        Trả về dict {label: count}.
        """
        students = self.repo.find_all()
        ranges = [
            ("0–0.4", 0.0, 0.4),
            ("0.4–0.8", 0.4, 0.8),
            ("0.8–1.2", 0.8, 1.2),
            ("1.2–1.6", 1.2, 1.6),
            ("1.6–2.0", 1.6, 2.0),
            ("2.0–2.4", 2.0, 2.4),
            ("2.4–2.8", 2.4, 2.8),
            ("2.8–3.2", 2.8, 3.2),
            ("3.2–3.6", 3.2, 3.6),
            ("3.6–4.0", 3.6, 4.01),
        ]
        counts = {label: 0 for label, _, _ in ranges}

        for student in students:
            gpa = student.gpa
            if gpa is None:
                continue
            try:
                gpa = float(gpa)
            except (ValueError, TypeError):
                continue
            for label, lo, hi in ranges:
                if lo <= gpa < hi:
                    counts[label] += 1
                    break

        return counts

    def get_scholarship_emails(self):
        """Trả về danh sách email của sinh viên được học bổng."""
        students = self.repo.find_all()
        return [s.email for s in students if s.scholarship == "Yes" and s.email]