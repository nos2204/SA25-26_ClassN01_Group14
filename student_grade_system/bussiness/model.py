"""
Layer 2 – Business Logic: Định nghĩa Student entity
Được dùng xuyên suốt toàn bộ ứng dụng.
"""

class Student:
    """Đối tượng nghiệp vụ đại diện cho một sinh viên."""

    def __init__(self, dep, student_id, name, division, gender,
                 email, dob, grade, credits, gpa=None, scholarship=None):
        self.dep = dep
        self.student_id = student_id
        self.name = name
        self.division = division
        self.gender = gender
        self.email = email
        self.dob = str(dob) if dob else None  # Chuyển datetime của MySQL sang string để dễ format JSON
        self.grade = grade
        self.credits = int(credits) if credits is not None else 0
        self.gpa = float(gpa) if gpa is not None else 0.0
        self.scholarship = float(scholarship) if scholarship is not None else 0.0

    def to_dict(self):
        """Chuyển đổi sang dictionary để Presentation Layer sử dụng (JSON / UI)."""
        return {
            "dep": self.dep,
            "student_id": self.student_id,
            "name": self.name,
            "division": self.division,
            "gender": self.gender,
            "email": self.email,
            "dob": self.dob,
            "grade": self.grade,
            "credits": self.credits,
            "gpa": self.gpa,
            "scholarship": self.scholarship,
        }

    @staticmethod
    def from_db_row(row):
        """
        Tạo Student từ một hàng dữ liệu MySQL (tuple).
        Giả định thứ tự các cột trong câu lệnh SELECT MySQL là:
        0:dep, 1:student_id, 2:name, 3:division, 4:gender, 5:email, 6:dob, 7:grade, 8:gpa, 9:credits, 10:scholarship
        """
        if not row:
            return None
            
        return Student(
            dep=row[0],
            student_id=row[1],
            name=row[2],
            division=row[3],
            gender=row[4],
            email=row[5],
            dob=row[6],
            grade=row[7],
            gpa=row[8],          # Map chính xác vị trí cột gpa trong DB
            credits=row[9],      # Map chính xác vị trí cột credits trong DB
            scholarship=row[10]  # Map chính xác vị trí cột scholarship trong DB
        )