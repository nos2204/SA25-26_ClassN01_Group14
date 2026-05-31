import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import jwt
from datetime import datetime, timedelta
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, send_file, jsonify, abort, g)
from dotenv import load_dotenv

from persistence.models import (db, UserModel, StudentModel, SubjectModel,
                                 GradeModel, SemesterModel, AuditLog,
                                 DepartmentModel)
from business.student_service import StudentService
from gateway import (token_required, admin_required, admin_or_self_required,
                     generate_csrf_token, validate_csrf,
                     check_brute_force, record_failed_login, record_success_login)

base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, '.env'))

app = Flask(
    __name__,
    template_folder='presentation/templates',
    static_folder='presentation/static'
)

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'quanlidiemsinhvien_secret_key_2026')

# --- ĐÃ CHỈNH SỬA: Ép kết nối thẳng vào MySQL Server của bạn ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root@127.0.0.1:3306/quanlidiemsinhvien'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

db.init_app(app)


@app.context_processor
def inject_globals():
    return {
        'csrf_token': generate_csrf_token,
        'now': datetime.utcnow,
    }


@app.before_request
def csrf_protect():
    exempt = {'login', 'static'}
    if request.endpoint in exempt:
        return
    validate_csrf()


_db_initialized = False

@app.before_request
def setup_db():
    global _db_initialized
    if _db_initialized:
        return
    _db_initialized = True
    try:
        # 1. Tạo bảng tự động theo cấu trúc Class Models
        db.create_all()
        
        # 2. CẬP NHẬT: Tự động bổ sung các cột còn thiếu trực tiếp vào MySQL bằng SQL thuần
        alter_queries = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS student_id INT NULL;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_count INT DEFAULT 0;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until DATETIME NULL;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS gender VARCHAR(10) NULL;",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS email VARCHAR(100) NULL;",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS academic_rank VARCHAR(50) NULL;"
        ]
        
        for query in alter_queries:
            try:
                db.session.execute(db.text(query))
            except Exception:
                # Phương án dự phòng nếu MySQL phiên bản cũ không nhận diện được cú pháp 'IF NOT EXISTS'
                try:
                    clean_query = query.replace("IF NOT EXISTS ", "")
                    db.session.execute(db.text(clean_query))
                except Exception:
                    pass  # Nếu cột đã tồn tại rồi thì bỏ qua không báo lỗi bậy
        db.session.commit()

        # 3. Khởi tạo tài khoản admin và dữ liệu mẫu nếu chưa có
        if not UserModel.query.filter_by(username='admin').first():
            admin = UserModel(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
        if not SemesterModel.query.first():
            sem = SemesterModel(name='Học kỳ 1', academic_year='2024-2025', is_current=True)
            db.session.add(sem)
        db.session.commit()
    except Exception as e:
        print(f'[LỖI DATABASE]: {e}')


def generate_jwt_token(username, role):
    payload = {
        'exp': datetime.utcnow() + timedelta(hours=2),
        'sub': username,
        'role': role,
    }
    return jwt.encode(payload, app.secret_key, algorithm='HS256')


@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html', error=str(e)), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user     = UserModel.query.filter_by(username=username).first()

        locked, wait = check_brute_force(user)
        if locked:
            flash(f'Tài khoản bị khoá tạm thời. Thử lại sau {wait}.', 'danger')
            return render_template('login.html')

        if user and user.check_password(password):
            record_success_login(user)
            session['token']             = generate_jwt_token(user.username, user.role)
            session['username']          = user.username
            session['role']              = user.role
            session['linked_student_id'] = user.student_id
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('dashboard'))

        if user:
            record_failed_login(user)
            remaining = max(0, (user.failed_login_count or 0))
            left = max(0, 5 - remaining)
            flash(f'Sai tài khoản hoặc mật khẩu. Còn {left} lần thử.', 'danger')
        else:
            flash('Tài khoản không tồn tại.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@token_required
def dashboard():
    stats = StudentService.get_dashboard_stats()
    return render_template('dashboard.html', **stats)


@app.route('/profile', methods=['GET', 'POST'])
@token_required
def my_profile():
    if session.get('role') != 'student':
        return redirect(url_for('dashboard'))

    student = StudentModel.query.get_or_404(session['linked_student_id'])

    if request.method == 'POST':
        email = request.form.get('email', '').strip() or None
        phone = request.form.get('phone', '').strip() or None
        addr  = request.form.get('address', '').strip() or None
        student.email   = email
        student.phone   = phone
        student.address = addr
        db.session.commit()
        flash('Đã cập nhật thông tin cá nhân!', 'success')
        return redirect(url_for('my_profile'))

    semesters = SemesterModel.query.order_by(SemesterModel.academic_year.desc()).all()
    return render_template('profile.html', student=student, semesters=semesters)


@app.route('/students')
@token_required
def students_manager():
    keyword       = request.args.get('q', '').strip()
    gender        = request.args.get('gender', '')
    rank          = request.args.get('rank', '')
    department_id = request.args.get('department_id', '')
    page          = request.args.get('page', 1, type=int)

    students, total_pages, total = StudentService.search_students(
        keyword=keyword, gender=gender, rank=rank,
        department_id=department_id, page=page
    )
    departments = DepartmentModel.query.order_by(DepartmentModel.department_name).all()
    return render_template(
        'students.html',
        students=students, keyword=keyword, gender=gender,
        rank=rank, department_id=department_id,
        page=page, total_pages=total_pages, total=total,
        departments=departments,
    )


@app.route('/students/add', methods=['GET', 'POST'])
@token_required
@admin_required
def add_student():
    if request.method == 'POST':
        code = request.form.get('student_code', '').strip()
        if StudentModel.query.filter_by(student_code=code).first():
            flash(f'MSSV "{code}" đã tồn tại!', 'danger')
            return redirect(url_for('add_student'))

        dob_str = request.form.get('date_of_birth', '')
        dob     = datetime.strptime(dob_str, '%Y-%m-%d').date() if dob_str else None
        dept_id = request.form.get('department_id') or None

        student = StudentModel(
            student_code  = code,
            full_name     = request.form.get('full_name', '').strip(),
            gender        = request.form.get('gender', 'Nam'),
            email         = request.form.get('email', '').strip() or None,
            phone         = request.form.get('phone', '').strip() or None,
            class_name    = request.form.get('class_name', '').strip() or None,
            address       = request.form.get('address', '').strip() or None,
            date_of_birth = dob,
            department_id = dept_id,
        )
        db.session.add(student)
        db.session.commit()
        flash(f'Đã thêm sinh viên {student.full_name} thành công!', 'success')
        return redirect(url_for('students_manager'))

    departments = DepartmentModel.query.order_by(DepartmentModel.department_name).all()
    return render_template('student_form.html', student=None, action='add',
                           departments=departments)


@app.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@token_required
@admin_required
def edit_student(student_id):
    student = StudentModel.query.get_or_404(student_id)
    if request.method == 'POST':
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
        dept_id = request.form.get('department_id') or None

        student.student_code  = code
        student.full_name     = request.form.get('full_name', '').strip()
        student.gender        = request.form.get('gender', 'Nam')
        student.email         = request.form.get('email', '').strip() or None
        student.phone         = request.form.get('phone', '').strip() or None
        student.class_name    = request.form.get('class_name', '').strip() or None
        student.address       = request.form.get('address', '').strip() or None
        student.date_of_birth = dob
        student.department_id = dept_id
        db.session.commit()
        flash('Cập nhật thông tin sinh viên thành công!', 'success')
        return redirect(url_for('students_manager'))

    departments = DepartmentModel.query.order_by(DepartmentModel.department_name).all()
    return render_template('student_form.html', student=student, action='edit',
                           departments=departments)


@app.route('/students/<int:student_id>/delete', methods=['POST'])
@token_required
@admin_required
def delete_student(student_id):
    student = StudentModel.query.get_or_404(student_id)
    name    = student.full_name
    db.session.delete(student)
    db.session.commit()
    flash(f'Đã xóa sinh viên {name}.', 'success')
    return redirect(url_for('students_manager'))


@app.route('/students/import', methods=['GET', 'POST'])
@token_required
@admin_required
def import_students():
    if request.method == 'POST':
        f = request.files.get('csv_file')
        if not f or not f.filename.endswith('.csv'):
            flash('Vui lòng chọn file CSV hợp lệ.', 'danger')
            return redirect(url_for('import_students'))

        added, skipped, errors = StudentService.import_students_from_csv(
            f.stream, actor=session['username']
        )
        flash(f'Import hoàn tất: thêm mới {added}, bỏ qua {skipped} (trùng MSSV).', 'success')
        if errors:
            for err in errors[:10]:
                flash(err, 'warning')
        return redirect(url_for('students_manager'))

    return render_template('import_students.html')


@app.route('/students/<int:student_id>/grades', methods=['GET', 'POST'])
@token_required
@admin_or_self_required
def manage_grades(student_id):
    student   = StudentModel.query.get_or_404(student_id)
    subjects  = SubjectModel.query.order_by(SubjectModel.subject_name).all()
    semesters = SemesterModel.query.order_by(
        SemesterModel.academic_year.desc(), SemesterModel.name
    ).all()

    sel_sem_id = request.args.get('semester_id', type=int)
    if not sel_sem_id:
        current = SemesterModel.query.filter_by(is_current=True).first()
        sel_sem_id = current.id if current else (semesters[0].id if semesters else None)

    grades = {}
    if sel_sem_id:
        grades = {g.subject_id: g for g in
                  GradeModel.query.filter_by(student_id=student_id,
                                             semester_id=sel_sem_id).all()}

    if request.method == 'POST' and session.get('role') == 'admin':
        if not sel_sem_id:
            flash('Không có học kỳ nào để lưu điểm!', 'danger')
            return redirect(url_for('manage_grades', student_id=student_id))

        for subject in subjects:
            pg_key = f'progress_{subject.id}'
            eg_key = f'exam_{subject.id}'
            if pg_key in request.form and eg_key in request.form:
                try:
                    pg = float(request.form[pg_key])
                    eg = float(request.form[eg_key])
                    if 0 <= pg <= 10 and 0 <= eg <= 10:
                        StudentService.upsert_grade(
                            student_id, subject.id, sel_sem_id,
                            pg, eg, actor=session['username']
                        )
                except ValueError:
                    pass
        flash('Đã cập nhật điểm và tính lại GPA!', 'success')
        return redirect(url_for('manage_grades', student_id=student_id,
                                semester_id=sel_sem_id))

    sem_gpa = StudentService.calculate_student_gpa(student_id, sel_sem_id) if sel_sem_id else 0
    student = StudentModel.query.get(student_id)
    return render_template('grades.html',
                           student=student, subjects=subjects,
                           grades=grades, semesters=semesters,
                           sel_sem_id=sel_sem_id, sem_gpa=sem_gpa)


@app.route('/grades/import', methods=['GET', 'POST'])
@token_required
@admin_required
def import_grades():
    semesters = SemesterModel.query.order_by(
        SemesterModel.academic_year.desc(), SemesterModel.name
    ).all()

    if request.method == 'POST':
        f   = request.files.get('csv_file')
        sid = request.form.get('semester_id', type=int)
        if not f or not f.filename.endswith('.csv') or not sid:
            flash('Vui lòng chọn file CSV và học kỳ.', 'danger')
            return redirect(url_for('import_grades'))

        updated, errors = StudentService.import_grades_from_csv(
            f.stream, semester_id=sid, actor=session['username']
        )
        flash(f'Import điểm hoàn tất: cập nhật {updated} bản ghi.', 'success')
        for err in errors[:10]:
            flash(err, 'warning')
        return redirect(url_for('students_manager'))

    return render_template('import_grades.html', semesters=semesters)


@app.route('/students/<int:student_id>/transcript.pdf')
@token_required
@admin_or_self_required
def export_transcript_pdf(student_id):
    sem_id = request.args.get('semester_id', type=int)
    try:
        pdf_bytes = StudentService.export_transcript_pdf(student_id, sem_id)
    except RuntimeError as e:
        flash(str(e), 'danger')
        return redirect(url_for('manage_grades', student_id=student_id))

    from flask import Response
    student = StudentModel.query.get(student_id)
    filename = f"bangdiem_{student.student_code}.pdf"
    return Response(pdf_bytes, mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename={filename}'})


@app.route('/subjects')
@token_required
@admin_required
def subjects_manager():
    subjects    = SubjectModel.query.order_by(SubjectModel.subject_code).all()
    departments = DepartmentModel.query.order_by(DepartmentModel.department_name).all()
    return render_template('subjects.html', subjects=subjects, departments=departments)


@app.route('/subjects/add', methods=['POST'])
@token_required
@admin_required
def add_subject():
    code = request.form.get('subject_code', '').strip()
    if SubjectModel.query.filter_by(subject_code=code).first():
        flash(f'Mã môn học "{code}" đã tồn tại!', 'danger')
        return redirect(url_for('subjects_manager'))
    subject = SubjectModel(
        subject_code  = code,
        subject_name  = request.form.get('subject_name', '').strip(),
        credits       = int(request.form.get('credits', 3)),
        department_id = request.form.get('department_id') or None,
    )
    db.session.add(subject)
    db.session.commit()
    flash('Đã thêm môn học!', 'success')
    return redirect(url_for('subjects_manager'))


@app.route('/subjects/<int:subject_id>/edit', methods=['POST'])
@token_required
@admin_required
def edit_subject(subject_id):
    subject = SubjectModel.query.get_or_404(subject_id)
    subject.subject_name  = request.form.get('subject_name', subject.subject_name).strip()
    subject.credits       = int(request.form.get('credits', subject.credits))
    subject.department_id = request.form.get('department_id') or None
    db.session.commit()
    flash('Đã cập nhật môn học!', 'success')
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


@app.route('/semesters')
@token_required
@admin_required
def semesters_manager():
    semesters = SemesterModel.query.order_by(
        SemesterModel.academic_year.desc(), SemesterModel.name
    ).all()
    return render_template('semesters.html', semesters=semesters)


@app.route('/semesters/add', methods=['POST'])
@token_required
@admin_required
def add_semester():
    name  = request.form.get('name', '').strip()
    year  = request.form.get('academic_year', '').strip()
    is_cur = bool(request.form.get('is_current'))

    if SemesterModel.query.filter_by(name=name, academic_year=year).first():
        flash('Học kỳ này đã tồn tại!', 'danger')
        return redirect(url_for('semesters_manager'))

    if is_cur:
        SemesterModel.query.update({'is_current': False})

    sem = SemesterModel(name=name, academic_year=year, is_current=is_cur)
    db.session.add(sem)
    db.session.commit()
    flash(f'Đã thêm {sem.display_name}.', 'success')
    return redirect(url_for('semesters_manager'))


@app.route('/semesters/<int:sem_id>/set_current', methods=['POST'])
@token_required
@admin_required
def set_current_semester(sem_id):
    SemesterModel.query.update({'is_current': False})
    sem = SemesterModel.query.get_or_404(sem_id)
    sem.is_current = True
    db.session.commit()
    flash(f'Đã đặt "{sem.display_name}" làm học kỳ hiện tại.', 'success')
    return redirect(url_for('semesters_manager'))


@app.route('/semesters/<int:sem_id>/delete', methods=['POST'])
@token_required
@admin_required
def delete_semester(sem_id):
    sem = SemesterModel.query.get_or_404(sem_id)
    if GradeModel.query.filter_by(semester_id=sem_id).count() > 0:
        flash('Không thể xóa học kỳ đã có điểm!', 'danger')
        return redirect(url_for('semesters_manager'))
    db.session.delete(sem)
    db.session.commit()
    flash('Đã xóa học kỳ.', 'success')
    return redirect(url_for('semesters_manager'))


@app.route('/departments')
@token_required
@admin_required
def departments_manager():
    departments = DepartmentModel.query.order_by(DepartmentModel.department_name).all()
    return render_template('departments.html', departments=departments)


@app.route('/departments/add', methods=['POST'])
@token_required
@admin_required
def add_department():
    code = request.form.get('department_code', '').strip()
    if DepartmentModel.query.filter_by(department_code=code).first():
        flash(f'Mã khoa "{code}" đã tồn tại!', 'danger')
        return redirect(url_for('departments_manager'))
    dept = DepartmentModel(
        department_code = code,
        department_name = request.form.get('department_name', '').strip(),
    )
    db.session.add(dept)
    db.session.commit()
    flash('Đã thêm khoa mới.', 'success')
    return redirect(url_for('departments_manager'))


@app.route('/departments/<int:dept_id>/delete', methods=['POST'])
@token_required
@admin_required
def delete_department(dept_id):
    dept = DepartmentModel.query.get_or_404(dept_id)
    if dept.students or dept.subjects:
        flash('Không thể xóa khoa đang có sinh viên hoặc môn học!', 'danger')
        return redirect(url_for('departments_manager'))
    db.session.delete(dept)
    db.session.commit()
    flash('Đã xóa khoa.', 'success')
    return redirect(url_for('departments_manager'))


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
    flash('Đã tạo tài khoản!', 'success')
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
    user.reset_lock()
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
    if request.method == 'POST':
        user     = UserModel.query.filter_by(username=session['username']).first()
        old_pass = request.form.get('old_password', '')
        new_pass = request.form.get('new_password', '').strip()
        confirm  = request.form.get('confirm_password', '').strip()
        if not user.check_password(old_pass):
            flash('Mật khẩu hiện tại không đúng!', 'danger')
        elif len(new_pass) < 6:
            flash('Mật khẩu mới phải có ít nhất 6 ký tự!', 'danger')
        elif new_pass != confirm:
            flash('Xác nhận mật khẩu không khớp!', 'danger')
        else:
            user.set_password(new_pass)
            db.session.commit()
            flash('Đổi mật khẩu thành công!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('change_password.html')


@app.route('/audit')
@token_required
@admin_required
def audit_log():
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=30, error_out=False
    )
    return render_template('audit_log.html', logs=logs)


@app.route('/export')
@token_required
@admin_required
def export_excel():
    sem_id = request.args.get('semester_id', type=int)
    path   = '/tmp/baocao_sinhvien.xlsx'
    StudentService.export_students_to_excel(path, semester_id=sem_id)
    return send_file(path, as_attachment=True, download_name='baocao_sinhvien.xlsx')


if __name__ == '__main__':
    os.makedirs(os.path.join(base_dir, 'instance'), exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)