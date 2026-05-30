# app.py  —  Tầng Presentation: định tuyến URL & điều phối request
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import jwt
from datetime import datetime, timedelta
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, send_file, jsonify)
from dotenv import load_dotenv

from persistence.models import db, UserModel, StudentModel, SubjectModel, GradeModel
from business.student_service import StudentService
from gateway import token_required, admin_required, admin_or_self_required

# Nạp biến môi trường
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, '.env')
load_dotenv(env_path)

# =========================================================================
# Khởi tạo Flask
# =========================================================================
app = Flask(
    __name__,
    template_folder='presentation/templates',
    static_folder='presentation/static'
)

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'quanlidiemsinhvien_secret_key_2026')

# --- THAY ĐỔI TẠI ĐÂY: Chuyển cấu hình kết nối từ MySQL sang SQLite ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///student.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


def generate_jwt_token(username, role):
    payload = {
        'exp': datetime.utcnow() + timedelta(hours=2),
        'sub': username,
        'role': role,
    }
    return jwt.encode(payload, app.secret_key, algorithm='HS256')


# =========================================================================
# Tự động tạo bảng & tài khoản admin mặc định
# =========================================================================
@app.before_request
def setup_db():
    if setup_db in app.before_request_funcs.get(None, []):
        app.before_request_funcs[None].remove(setup_db)
    try:
        db.create_all()
        if not UserModel.query.filter_by(username='admin').first():
            admin = UserModel(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
    except Exception as e:
        print(f'[LỖI DATABASE]: {e}')


# =========================================================================
# Auth
# =========================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = UserModel.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['token']              = generate_jwt_token(user.username, user.role)
            session['username']           = user.username
            session['role']               = user.role
            session['linked_student_id']  = user.student_id  # None nếu là admin
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('dashboard'))
        flash('Tài khoản hoặc mật khẩu không chính xác.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# =========================================================================
# Dashboard
# =========================================================================
@app.route('/')
@token_required
def dashboard():
    stats = StudentService.get_dashboard_stats()
    return render_template('dashboard.html', **stats)


# =========================================================================
# Quản lý Sinh viên
# =========================================================================
@app.route('/students')
@token_required
def students_manager():
    keyword  = request.args.get('q', '').strip()
    gender   = request.args.get('gender', '')
    rank     = request.args.get('rank', '')
    page     = request.args.get('page', 1, type=int)

    students, total_pages, total = StudentService.search_students(
        keyword=keyword, gender=gender, rank=rank, page=page
    )
    return render_template(
        'students.html',
        students=students,
        keyword=keyword,
        gender=gender,
        rank=rank,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@app.route('/students/add', methods=['GET', 'POST'])
@token_required
@admin_required   # ← đặt đúng vị trí: sau @token_required, trên route handler
def add_student():
    if request.method == 'POST':
        code = request.form.get('student_code', '').strip()
        if StudentModel.query.filter_by(student_code=code).first():
            flash(f'MSSV "{code}" đã tồn tại trong hệ thống!', 'danger')
            return redirect(url_for('add_student'))

        dob_str = request.form.get('date_of_birth', '')
        dob     = datetime.strptime(dob_str, '%Y-%m-%d').date() if dob_str else None

        student = StudentModel(
            student_code  = code,
            full_name     = request.form.get('full_name', '').strip(),
            gender        = request.form.get('gender', 'Nam'),
            email         = request.form.get('email', '').strip() or None,
            phone         = request.form.get('phone', '').strip() or None,
            class_name    = request.form.get('class_name', '').strip() or None,
            date_of_birth = dob,
        )
        db.session.add(student)
        db.session.commit()
        flash(f'Đã thêm sinh viên {student.full_name} thành công!', 'success')
        return redirect(url_for('students_manager'))

    return render_template('student_form.html', student=None, action='add')


@app.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@token_required
@admin_required
def edit_student(student_id):
    student = StudentModel.query.get_or_404(student_id)
    if request.method == 'POST':
        # Kiểm tra trùng MSSV (trừ chính nó)
        code = request.form.get('student_code', '').strip()
        dup  = StudentModel.query.filter(
            StudentModel.student_code == code,
            StudentModel.id != student_id
        ).first()
        if dup:
            flash(f'MSSV "{code}" đã tồn tại!', 'danger')
            return redirect(url_for('edit_student', student_id=student_id))

        dob_str = request.form.get('date_of_birth', '')
        dob     = datetime.strptime(dob_str, '%Y-%m-%d').date() if dob_str else None

        student.student_code  = code
        student.full_name     = request.form.get('full_name', '').strip()
        student.gender        = request.form.get('gender', 'Nam')
        student.email         = request.form.get('email', '').strip() or None
        student.phone         = request.form.get('phone', '').strip() or None
        student.class_name    = request.form.get('class_name', '').strip() or None
        student.date_of_birth = dob
        db.session.commit()
        flash('Cập nhật thông tin sinh viên thành công!', 'success')
        return redirect(url_for('students_manager'))

    return render_template('student_form.html', student=student, action='edit')


@app.route('/students/<int:student_id>/delete', methods=['POST'])
@token_required
@admin_required
def delete_student(student_id):
    student = StudentModel.query.get_or_404(student_id)
    name    = student.full_name
    db.session.delete(student)
    db.session.commit()
    flash(f'Đã xóa sinh viên {name} khỏi hệ thống.', 'success')
    return redirect(url_for('students_manager'))


# =========================================================================
# Quản lý Điểm
# =========================================================================
@app.route('/students/<int:student_id>/grades', methods=['GET', 'POST'])
@token_required
@admin_or_self_required
def manage_grades(student_id):
    student  = StudentModel.query.get_or_404(student_id)
    subjects = SubjectModel.query.order_by(SubjectModel.subject_name).all()
    grades   = {g.subject_id: g for g in student.grades}

    if request.method == 'POST' and session.get('role') == 'admin':
        for subject in subjects:
            pg_key = f'progress_{subject.id}'
            eg_key = f'exam_{subject.id}'
            if pg_key in request.form and eg_key in request.form:
                try:
                    pg = float(request.form[pg_key])
                    eg = float(request.form[eg_key])
                    if 0 <= pg <= 10 and 0 <= eg <= 10:
                        StudentService.upsert_grade(student_id, subject.id, pg, eg)
                except ValueError:
                    pass
        flash('Đã cập nhật điểm và tính lại GPA!', 'success')
        return redirect(url_for('manage_grades', student_id=student_id))

    # Reload student để lấy GPA mới
    student = StudentModel.query.get(student_id)
    return render_template('grades.html', student=student,
                           subjects=subjects, grades=grades)


# =========================================================================
# Quản lý Môn học
# =========================================================================
@app.route('/subjects')
@token_required
@admin_required
def subjects_manager():
    subjects = SubjectModel.query.order_by(SubjectModel.subject_code).all()
    return render_template('subjects.html', subjects=subjects)


@app.route('/subjects/add', methods=['POST'])
@token_required
@admin_required
def add_subject():
    code = request.form.get('subject_code', '').strip()
    if SubjectModel.query.filter_by(subject_code=code).first():
        flash(f'Mã môn học "{code}" đã tồn tại!', 'danger')
        return redirect(url_for('subjects_manager'))
    subject = SubjectModel(
        subject_code = code,
        subject_name = request.form.get('subject_name', '').strip(),
        credits      = int(request.form.get('credits', 3)),
    )
    db.session.add(subject)
    db.session.commit()
    flash('Đã thêm môn học thành công!', 'success')
    return redirect(url_for('subjects_manager'))


@app.route('/subjects/<int:subject_id>/delete', methods=['POST'])
@token_required
@admin_required
def delete_subject(subject_id):
    subject = SubjectModel.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    flash('Đã xóa môn học.', 'success')
    return redirect(url_for('subjects_manager'))


# =========================================================================
# Quản lý Tài khoản (chỉ Admin)
# =========================================================================
@app.route('/users')
@token_required
@admin_required
def users_manager():
    users = UserModel.query.order_by(UserModel.username).all()
    students_no_account = (StudentModel.query
                           .filter(~StudentModel.id.in_(
                               db.session.query(UserModel.student_id)
                               .filter(UserModel.student_id.isnot(None))
                           ))
                           .order_by(StudentModel.full_name).all())
    return render_template('users.html', users=users,
                           students_no_account=students_no_account)


@app.route('/users/add', methods=['POST'])
@token_required
@admin_required
def add_user():
    uname = request.form.get('username', '').strip()
    if UserModel.query.filter_by(username=uname).first():
        flash(f'Tên đăng nhập "{uname}" đã tồn tại!', 'danger')
        return redirect(url_for('users_manager'))
    user = UserModel(
        username   = uname,
        role       = request.form.get('role', 'student'),
        student_id = request.form.get('student_id') or None,
    )
    user.set_password(request.form.get('password', ''))
    db.session.add(user)
    db.session.commit()
    flash('Đã tạo tài khoản thành công!', 'success')
    return redirect(url_for('users_manager'))


@app.route('/users/<int:user_id>/reset_password', methods=['POST'])
@token_required
@admin_required
def reset_password(user_id):
    user     = UserModel.query.get_or_404(user_id)
    new_pass = request.form.get('new_password', '').strip()
    if len(new_pass) < 6:
        flash('Mật khẩu mới phải có ít nhất 6 ký tự!', 'danger')
        return redirect(url_for('users_manager'))
    user.set_password(new_pass)
    db.session.commit()
    flash(f'Đã đặt lại mật khẩu cho {user.username}.', 'success')
    return redirect(url_for('users_manager'))


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@token_required
@admin_required
def delete_user(user_id):
    user = UserModel.query.get_or_404(user_id)
    if user.username == 'admin':
        flash('Không thể xóa tài khoản admin gốc!', 'danger')
        return redirect(url_for('users_manager'))
    db.session.delete(user)
    db.session.commit()
    flash('Đã xóa tài khoản.', 'success')
    return redirect(url_for('users_manager'))


@app.route('/change_password', methods=['GET', 'POST'])
@token_required
def change_password():
    """Cho phép mọi user tự đổi mật khẩu của mình."""
    if request.method == 'POST':
        user     = UserModel.query.filter_by(username=session['username']).first()
        old_pass = request.form.get('old_password', '')
        new_pass = request.form.get('new_password', '').strip()
        if not user.check_password(old_pass):
            flash('Mật khẩu hiện tại không đúng!', 'danger')
        elif len(new_pass) < 6:
            flash('Mật khẩu mới phải có ít nhất 6 ký tự!', 'danger')
        else:
            user.set_password(new_pass)
            db.session.commit()
            flash('Đổi mật khẩu thành công!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('change_password.html')


# =========================================================================
# Export
# =========================================================================
@app.route('/export')
@token_required
@admin_required
def export_excel():
    path = '/tmp/baocao_sinhvien.xlsx'
    StudentService.export_students_to_excel(path)
    return send_file(path, as_attachment=True,
                     download_name='baocao_sinhvien.xlsx')


# =========================================================================
# Chạy server
# =========================================================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)