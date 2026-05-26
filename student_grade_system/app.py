"""
Layer 1 – Presentation: Tkinter UI Controller
Điểm vào chính của ứng dụng quản lý sinh viên.

Kiến trúc phân lớp (Layered Architecture):
  Presentation (app.py / UI)
      ↓ gọi xuống
  Business Logic (student_service.py)
      ↓ gọi xuống
  Persistence (student_repository.py)
      ↓ truy cập
  Data Layer (MySQL)
"""

import os
import smtplib

import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image, ImageTk
from tkinter import *
from tkinter import filedialog, messagebox, ttk

from business_logic.student_service import StudentService
from emailAccount import app_password, email_account

# ── Điều chỉnh đường dẫn ảnh (chạy được từ bất kỳ thư mục nào) ──────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "college_images")


def img_path(filename):
    return os.path.join(IMG_DIR, filename)


class StudentApp:
    """
    Layer 1: Presentation Layer.
    Nhận sự kiện UI → gọi StudentService (Layer 2) → hiển thị kết quả.
    KHÔNG chứa SQL, KHÔNG chứa quy tắc nghiệp vụ.
    """

    def __init__(self, root: Tk):
        self.root = root
        self.root.geometry("1530x790+0+0")
        self.root.title("ĐẠI HỌC ABC – QUẢN LÝ SINH VIÊN")

        # Kết nối với Business Logic Layer
        self.service = StudentService()

        # ── Biến liên kết UI ─────────────────────────────────────────────────
        self.var_dep = StringVar()
        self.var_course = StringVar()
        self.var_year = StringVar()
        self.var_semester = StringVar()
        self.var_std_id = StringVar()
        self.var_std_name = StringVar()
        self.var_div = StringVar()
        self.var_gender = StringVar()
        self.var_phone = StringVar()
        self.var_address = StringVar()
        self.var_email = StringVar()
        self.var_dob = StringVar()
        self.var_grade = StringVar()
        self.var_avr = StringVar()
        self.var_scholarship = StringVar()
        self.var_credits = StringVar()

        self._build_ui()

    # =========================================================================
    # UI BUILD
    # =========================================================================

    def _build_ui(self):
        """Xây dựng toàn bộ giao diện."""

        # Banner ảnh header
        for idx, fname, x in [
            (1, "1.png", 0),
            (2, "2.png", 510),
            (3, "3.png", 1020),
        ]:
            try:
                img = Image.open(img_path(fname)).resize((540, 160), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                btn = Button(self.root, image=photo, cursor="hand2")
                btn.place(x=x, y=0, width=540, height=160)
                setattr(self, f"_header_img_{idx}", photo)  # giữ reference
            except FileNotFoundError:
                pass

        # Background
        try:
            bg_img = Image.open(img_path("uet_university.png")).resize((1530, 710), Image.LANCZOS)
            self._bg_photo = ImageTk.PhotoImage(bg_img)
            bg_lbl = Label(self.root, image=self._bg_photo, bd=2, relief=RIDGE)
        except FileNotFoundError:
            bg_lbl = Label(self.root, bg="#e8f4f8", bd=2, relief=RIDGE)
        bg_lbl.place(x=0, y=160, width=1530, height=710)

        Label(
            bg_lbl,
            text="ĐẠI HỌC ABC – CHƯƠNG TRÌNH QUẢN LÝ SINH VIÊN",
            font=("Times New Roman", 33, "bold"),
            fg="blue",
            bg="white",
        ).place(x=0, y=0, width=1530, height=50)

        # ── Main frame ──────────────────────────────────────────────────────
        manage_frame = Frame(bg_lbl, bd=2, relief=RIDGE, bg="white")
        manage_frame.place(x=15, y=55, width=1500, height=800)

        self._build_left_panel(manage_frame)
        self._build_right_panel(manage_frame)

    def _build_left_panel(self, parent):
        """Panel trái: form nhập liệu sinh viên."""
        left = LabelFrame(
            parent, bd=4, relief=RIDGE, padx=2,
            text="THÔNG TIN SINH VIÊN",
            font=("Times New Roman", 12, "bold"), fg="red", bg="white",
        )
        left.place(x=10, y=10, width=660, height=540)

        # Ảnh banner trong panel
        try:
            kinhte = Image.open(img_path("kinhte.png")).resize((550, 150), Image.LANCZOS)
            self._kinhte_photo = ImageTk.PhotoImage(kinhte)
            Label(left, image=self._kinhte_photo, bd=2, relief=RIDGE).place(x=0, y=0, width=650, height=120)
        except FileNotFoundError:
            Label(left, text="[Banner]", bg="lightgrey").place(x=0, y=0, width=650, height=120)

        # ── Ngành học ───────────────────────────────────────────────────────
        major_frame = LabelFrame(
            left, bd=4, relief=RIDGE, padx=2,
            text="Ngành học",
            font=("Times New Roman", 12, "bold"), fg="red", bg="white",
        )
        major_frame.place(x=0, y=120, width=650, height=70)

        Label(major_frame, text="Major", font=("Arial", 12, "bold"), bg="white").grid(
            row=0, column=0, padx=2, sticky=W
        )
        combo_dep = ttk.Combobox(
            major_frame, textvariable=self.var_dep,
            font=("Arial", 12, "bold"), width=30, state="readonly",
        )
        combo_dep["values"] = (
            "Select Major",
            "Computer Science",
            "Computer Engineering",
            "Electrical Engineering",
            "Telecommunication Engineering",
        )
        combo_dep.current(0)
        combo_dep.grid(row=0, column=1, padx=2, pady=10, sticky=W)

        # ── Thông tin cá nhân ───────────────────────────────────────────────
        info_frame = LabelFrame(
            left, bd=4, relief=RIDGE, padx=2,
            text="Thông tin cá nhân",
            font=("Times New Roman", 12, "bold"), fg="red", bg="white",
        )
        info_frame.place(x=0, y=200, width=650, height=270)

        fields = [
            ("Student ID:", self.var_std_id, 0, 0, "Entry"),
            ("Student Name:", self.var_std_name, 0, 2, "Entry"),
            ("Class Division:", self.var_div, 1, 0, ("Select class", "Class1", "Class2", "Class3")),
            ("Credits:", self.var_credits, 1, 2, "Entry"),
            ("Gender:", self.var_gender, 2, 0, ("Select gender", "Male", "Female")),
            ("Date of Birth:", self.var_dob, 2, 2, "Entry"),
            ("Grade:", self.var_grade, 3, 0, "Entry"),
            ("Email:", self.var_email, 3, 2, "Entry"),
        ]

        for label_text, var, row, col, widget_type in fields:
            Label(info_frame, text=label_text, font=("Arial", 12, "bold"), bg="white").grid(
                row=row, column=col, sticky=W, padx=2, pady=7
            )
            if widget_type == "Entry":
                ttk.Entry(info_frame, textvariable=var, font=("Arial", 12, "bold"), width=17).grid(
                    row=row, column=col + 1, sticky=W, padx=2, pady=7
                )
            else:
                cb = ttk.Combobox(info_frame, textvariable=var, font=("Arial", 12, "bold"), width=17)
                cb["values"] = widget_type
                cb.current(0)
                cb.grid(row=row, column=col + 1, sticky=W, padx=2, pady=7)

        # Nút GPA tối đa
        Button(
            info_frame, text="GPA Tối đa",
            command=self._on_max_gpa,
            font=("Arial", 11, "bold"), width=17, bg="purple", fg="white",
        ).grid(row=4, column=0, padx=1)

        # ── Nút CRUD ────────────────────────────────────────────────────────
        btn_frame = Frame(left, bd=2, relief=RIDGE, bg="white")
        btn_frame.place(x=0, y=490, width=650, height=38)

        for text, cmd, col in [
            ("Add", self._on_add, 0),
            ("Update", self._on_update, 1),
            ("Delete", self._on_delete, 2),
            ("Reset", self._on_reset, 3),
        ]:
            Button(
                btn_frame, text=text, command=cmd,
                font=("Arial", 11, "bold"), width=17, bg="blue", fg="white",
            ).grid(row=0, column=col, padx=1)

    def _build_right_panel(self, parent):
        """Panel phải: tìm kiếm, sắp xếp và bảng danh sách sinh viên."""
        right = LabelFrame(
            parent, bd=4, relief=RIDGE, padx=2,
            text="Danh sách sinh viên & Các chức năng",
            font=("Times New Roman", 12, "bold"), fg="red", bg="white",
        )
        right.place(x=680, y=10, width=800, height=540)

        # ── Thanh công cụ ───────────────────────────────────────────────────
        tools = LabelFrame(
            right, bd=4, relief=RIDGE, padx=2,
            text="Các chức năng",
            font=("Times New Roman", 12, "bold"), fg="red", bg="white",
        )
        tools.place(x=0, y=0, width=790, height=170)

        # Tìm kiếm
        Label(tools, text="Tìm kiếm theo:", font=("Times New Roman", 11, "bold"),
              fg="red", bg="white").grid(row=0, column=0, sticky=W, padx=5)
        self.var_com_search = StringVar()
        cb_search = ttk.Combobox(tools, state="readonly", textvariable=self.var_com_search,
                                  font=("Arial", 12, "bold"), width=12)
        cb_search["values"] = ("Select search", "Name", "DOB", "StudentID")
        cb_search.current(0)
        cb_search.grid(row=0, column=1, sticky=W, padx=2)

        self.var_search = StringVar()
        ttk.Entry(tools, textvariable=self.var_search, width=15, font=("Arial", 11, "bold")).grid(
            row=0, column=2
        )
        Button(tools, text="Search", command=self._on_search,
               font=("Arial", 11, "bold"), width=12, bg="blue", fg="white").grid(row=0, column=3)

        # Sắp xếp
        Label(tools, text="Sắp xếp theo:", font=("Times New Roman", 11, "bold"),
              fg="red", bg="white").grid(row=1, column=0, sticky=W, padx=5)
        self.var_sort_by = StringVar()
        cb_sort = ttk.Combobox(tools, state="readonly", textvariable=self.var_sort_by,
                                font=("Arial", 12, "bold"), width=18)
        cb_sort["values"] = ("Select sort", "Name", "DOB", "StudentID", "Grade")
        cb_sort.current(0)
        cb_sort.grid(row=1, column=1, sticky=W)
        Button(tools, text="Sort", command=self._on_sort,
               font=("Arial", 11, "bold"), width=12, bg="blue", fg="white").grid(row=1, column=2, padx=5)

        # Row 2: các nút tiện ích
        Button(tools, text="Export Data", command=self._on_export,
               font=("Arial", 11, "bold"), width=20, bg="blue", fg="white").grid(row=2, column=0, padx=5)
        Button(tools, text="Calculate GPA & Scholarship", command=self._on_calculate_gpa,
               font=("Arial", 11, "bold"), width=25, bg="blue", fg="white").grid(row=2, column=1, padx=5)
        Button(tools, text="Show All", command=self._load_table,
               font=("Arial", 11, "bold"), width=12, bg="blue", fg="white").grid(row=2, column=2)
        Button(tools, text="Statistic GPA", command=self._on_statistic_gpa,
               font=("Arial", 11, "bold"), width=12, bg="blue", fg="white").grid(row=2, column=3)

        # Row 3: gửi email
        Button(tools, text="Send Email Scholarship", command=self._on_send_email,
               font=("Arial", 11, "bold"), width=20, bg="green", fg="white").grid(row=3, column=0, padx=5)

        # ── Bảng sinh viên ──────────────────────────────────────────────────
        table_frame = Frame(right, bd=4, relief=RIDGE)
        table_frame.place(x=0, y=170, width=790, height=340)

        scroll_x = ttk.Scrollbar(table_frame, orient=HORIZONTAL)
        scroll_y = ttk.Scrollbar(table_frame, orient=VERTICAL)
        self.student_table = ttk.Treeview(
            table_frame,
            columns=("dep", "id", "name", "div", "Gender", "Email", "DOB",
                     "Grade", "Average", "Credits", "Scholarship"),
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set,
        )
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.config(command=self.student_table.xview)
        scroll_y.config(command=self.student_table.yview)

        columns_cfg = [
            ("dep", "Major", 110),
            ("id", "StudentID", 100),
            ("name", "Student Name", 120),
            ("div", "Class Div", 90),
            ("Gender", "Gender", 80),
            ("Email", "Email", 140),
            ("DOB", "Date of Birth", 100),
            ("Grade", "Grade", 70),
            ("Average", "GPA", 70),
            ("Credits", "Credits", 80),
            ("Scholarship", "Scholarship", 100),
        ]
        self.student_table["show"] = "headings"
        for col_id, heading, width in columns_cfg:
            self.student_table.heading(col_id, text=heading)
            self.student_table.column(col_id, width=width)

        self.student_table.pack(fill=BOTH, expand=1)
        self.student_table.bind("<ButtonRelease>", self._on_row_select)

        self._load_table()

    # =========================================================================
    # HELPER: điền dữ liệu lên bảng
    # =========================================================================

    def _populate_table(self, students):
        """Xóa bảng và hiển thị danh sách students."""
        self.student_table.delete(*self.student_table.get_children())
        for s in students:
            row = (s.dep, s.student_id, s.name, s.division, s.gender,
                   s.email, s.dob, s.grade, s.gpa, s.credits, s.scholarship)
            if s.gpa is not None:
                try:
                    gpa_f = float(s.gpa)
                    tag = "low_gpa" if gpa_f <= 2.3 else ""
                except (ValueError, TypeError):
                    tag = ""
            else:
                tag = ""
            if tag:
                self.student_table.insert("", END, values=row, tags=(tag,))
            else:
                self.student_table.insert("", END, values=row)
        self.student_table.tag_configure("low_gpa", background="red")

    def _load_table(self):
        """Tải toàn bộ sinh viên từ Service Layer lên bảng."""
        try:
            students = self.service.get_all_students()
            self._populate_table(students)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self.root)

    # =========================================================================
    # EVENT HANDLERS (Presentation Layer nhận sự kiện → gọi Service Layer)
    # =========================================================================

    def _on_row_select(self, event=""):
        """Khi click hàng trên bảng: điền dữ liệu vào form."""
        row_id = self.student_table.focus()
        content = self.student_table.item(row_id)
        data = content.get("values", [])
        if not data:
            return
        self.var_dep.set(data[0])
        self.var_std_id.set(data[1])
        self.var_std_name.set(data[2])
        self.var_div.set(data[3])
        self.var_gender.set(data[4])
        self.var_email.set(data[5])
        self.var_dob.set(data[6])
        self.var_grade.set(data[7])
        self.var_avr.set(data[8] if len(data) > 8 else "")
        self.var_credits.set(data[9] if len(data) > 9 else "")
        self.var_scholarship.set(data[10] if len(data) > 10 else "")

    def _on_add(self):
        try:
            self.service.add_student(
                self.var_dep.get(), self.var_std_id.get(), self.var_std_name.get(),
                self.var_div.get(), self.var_gender.get(), self.var_email.get(),
                self.var_dob.get(), self.var_grade.get(), self.var_credits.get(),
            )
            self._load_table()
            messagebox.showinfo("Thành công", "Đã thêm sinh viên thành công.", parent=self.root)
        except ValueError as e:
            messagebox.showerror("Lỗi nhập liệu", str(e), parent=self.root)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self.root)

    def _on_update(self):
        if not messagebox.askyesno("Xác nhận", "Bạn có chắc muốn cập nhật?", parent=self.root):
            return
        try:
            self.service.update_student(
                self.var_dep.get(), self.var_std_id.get(), self.var_std_name.get(),
                self.var_div.get(), self.var_gender.get(), self.var_email.get(),
                self.var_dob.get(), self.var_grade.get(), self.var_credits.get(),
            )
            self._load_table()
            messagebox.showinfo("Thành công", "Đã cập nhật sinh viên.", parent=self.root)
        except ValueError as e:
            messagebox.showerror("Lỗi nhập liệu", str(e), parent=self.root)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self.root)

    def _on_delete(self):
        if not self.var_std_id.get():
            messagebox.showerror("Lỗi", "Vui lòng chọn sinh viên cần xóa.", parent=self.root)
            return
        if not messagebox.askyesno("Xác nhận", "Bạn có chắc muốn xóa sinh viên này?", parent=self.root):
            return
        try:
            deleted = self.service.delete_student(self.var_std_id.get())
            if deleted:
                self._load_table()
                messagebox.showinfo("Thành công", "Đã xóa sinh viên.", parent=self.root)
            else:
                messagebox.showerror("Lỗi", "Không tìm thấy sinh viên.", parent=self.root)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self.root)

    def _on_reset(self):
        self.var_dep.set("Select Major")
        for var in (self.var_std_id, self.var_std_name, self.var_div, self.var_gender,
                    self.var_email, self.var_dob, self.var_grade, self.var_credits,
                    self.var_avr, self.var_scholarship):
            var.set("")

    def _on_search(self):
        field = self.var_com_search.get()
        keyword = self.var_search.get()
        if not field or field == "Select search" or not keyword:
            messagebox.showerror("Lỗi", "Vui lòng chọn tiêu chí và nhập từ khóa.", parent=self.root)
            return
        try:
            students = self.service.search_students(field, keyword)
            self._populate_table(students)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self.root)

    def _on_sort(self):
        option = self.var_sort_by.get()
        if not option or option == "Select sort":
            messagebox.showerror("Lỗi", "Vui lòng chọn tiêu chí sắp xếp.", parent=self.root)
            return
        try:
            students = self.service.sort_students(option)
            self._populate_table(students)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self.root)

    def _on_calculate_gpa(self):
        try:
            low_gpa = self.service.calculate_gpa_and_scholarship()
            self._load_table()
            if low_gpa:
                messagebox.showwarning(
                    "Cảnh báo GPA thấp",
                    f"Sinh viên có GPA ≤ 2.3:\n{', '.join(low_gpa)}",
                    parent=self.root,
                )
            messagebox.showinfo("Thành công", "Đã cập nhật GPA và học bổng.", parent=self.root)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self.root)

    def _on_max_gpa(self):
        try:
            grade = float(self.var_grade.get())
            credits = int(self.var_credits.get())
            result = self.service.calculate_max_gpa(grade, credits)
            messagebox.showinfo(
                "GPA Tối đa",
                f"GPA tối đa có thể đạt: {result['gpa_max']}\n"
                f"Phân loại bằng: {result['classification']}",
                parent=self.root,
            )
        except ValueError as e:
            messagebox.showerror("Lỗi", f"Dữ liệu không hợp lệ: {e}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self.root)

    def _on_statistic_gpa(self):
        try:
            counts = self.service.get_gpa_statistics()
            labels = list(counts.keys())
            values = list(counts.values())
            plt.figure(figsize=(10, 5))
            plt.bar(labels, values, color="steelblue", width=0.6)
            plt.title("Thống kê GPA sinh viên")
            plt.xlabel("Khoảng GPA")
            plt.ylabel("Số lượng sinh viên")
            plt.xticks(rotation=30)
            plt.tight_layout()
            plt.show()
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self.root)

    def _on_export(self):
        try:
            students = self.service.get_all_students()
            columns = ["Major", "StudentID", "Name", "Division", "Gender",
                       "Email", "DOB", "Grade", "GPA", "Credits", "Scholarship"]
            data = [[s.dep, s.student_id, s.name, s.division, s.gender,
                     s.email, s.dob, s.grade, s.gpa, s.credits, s.scholarship]
                    for s in students]
            df = pd.DataFrame(data, columns=columns)

            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            )
            if file_path:
                df.to_excel(file_path, index=False)
                messagebox.showinfo("Thành công", f"Đã xuất dữ liệu sang:\n{file_path}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self.root)

    def _on_send_email(self):
        try:
            emails = self.service.get_scholarship_emails()
            if not emails:
                messagebox.showinfo("Thông báo", "Không có sinh viên nào được học bổng.", parent=self.root)
                return

            mail_content = (
                "Subject: =?utf-8?b?VGjDtG5nIGLDoW8gdmUgaOG7jWMgYuG7lW5n?=\r\n"
                "Content-Type: text/plain; charset=utf-8\r\n\r\n"
                "Kính gửi em,\n\n"
                "Đại học ABC trân trọng thông báo: Chúc mừng em đã nhận được học bổng kỳ này!\n"
                "Keep going!\n\nThân mến,\nPhòng Đào Tạo – Đại Học ABC."
            )

            session = smtplib.SMTP("smtp.gmail.com", 587)
            session.starttls()
            session.login(email_account, app_password)
            for addr in emails:
                session.sendmail(email_account, addr, mail_content.encode("utf-8"))
            session.quit()

            messagebox.showinfo("Thành công", f"Đã gửi email cho {len(emails)} sinh viên.", parent=self.root)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self.root)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = Tk()
    app = StudentApp(root)
    root.mainloop()