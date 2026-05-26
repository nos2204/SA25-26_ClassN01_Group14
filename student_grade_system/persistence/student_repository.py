"""
Layer 3 – Persistence: StudentRepository
Toàn bộ truy cập database MySQL được tập trung tại đây.
Business Logic Layer KHÔNG được viết SQL trực tiếp.
"""

import mysql.connector
from business_logic.models import Student
from SQLaccount import host_name, user_name, password_key, database_name


def _get_connection():
    """Tạo kết nối MySQL mới."""
    return mysql.connector.connect(
        host=host_name,
        user=user_name,
        password=password_key,
        database=database_name,
    )


class StudentRepository:
    """
    Layer 3: Ánh xạ Student entity sang bảng `student` trong MySQL.
    Thực thi các thao tác CRUD và trả về Student objects.
    """

    # ── CREATE ────────────────────────────────────────────────────────────────

    def create(self, dep, student_id, name, division, gender,
               email, dob, grade, credits):
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO student (Dep, StudentID, Name, Division, Gender, email, DOB, Grade, Credits) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (dep, student_id, name, division, gender, email, dob, grade, credits),
        )
        conn.commit()
        conn.close()
        return Student(dep, student_id, name, division, gender, email, dob, grade, credits)

    # ── READ ──────────────────────────────────────────────────────────────────

    def find_all(self):
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM student")
        rows = cur.fetchall()
        conn.close()
        return [Student.from_db_row(r) for r in rows]

    def find_by_id(self, student_id):
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM student WHERE StudentID = %s", (student_id,))
        row = cur.fetchone()
        conn.close()
        return Student.from_db_row(row) if row else None

    def find_all_sorted(self, column: str):
        # column đã được validate ở Service Layer nên an toàn
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM student ORDER BY {column}")
        rows = cur.fetchall()
        conn.close()
        return [Student.from_db_row(r) for r in rows]

    def search(self, column: str, keyword: str):
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            f"SELECT * FROM student WHERE {column} LIKE %s",
            (f"%{keyword}%",),
        )
        rows = cur.fetchall()
        conn.close()
        return [Student.from_db_row(r) for r in rows]

    # ── UPDATE ────────────────────────────────────────────────────────────────

    def update(self, dep, student_id, name, division, gender,
               email, dob, grade, credits):
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE student SET Dep=%s, Name=%s, Division=%s, Gender=%s, "
            "email=%s, DOB=%s, Grade=%s, Credits=%s WHERE StudentID=%s",
            (dep, name, division, gender, email, dob, grade, credits, student_id),
        )
        conn.commit()
        conn.close()
        return self.find_by_id(student_id)

    def update_gpa_scholarship(self, student_id, gpa, scholarship):
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE student SET gpa=%s, scholarship=%s WHERE StudentID=%s",
            (gpa, scholarship, student_id),
        )
        conn.commit()
        conn.close()

    # ── DELETE ────────────────────────────────────────────────────────────────

    def delete(self, student_id):
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM student WHERE StudentID=%s", (student_id,))
        affected = cur.rowcount
        conn.commit()
        conn.close()
        return affected > 0