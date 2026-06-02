import os
import sys
import tempfile
import re

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import jwt
from datetime import datetime, timedelta, timezone
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, send_file, jsonify, abort, g)
from dotenv import load_dotenv
from sqlalchemy import inspect as sa_inspect

from persistence.models import (db, UserModel, StudentModel, SubjectModel,
                                 GradeModel, SemesterModel, AuditLog,
                                 DepartmentModel, ClassModel, TeacherModel,
                                 CourseSectionModel, EnrollmentModel)
from business.student_service import StudentService
from gateway import (token_required, admin_required, admin_or_self_required,
                     admin_or_teacher_required, teacher_required,
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

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(base_dir, 'instance', 'student.db'))
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


def _add_column_if_missing(table_name, column_name, column_sql):
    """Bổ sung cột cho database cũ. Chạy được với SQLite và MySQL."""
    try:
        inspector = sa_inspect(db.engine)
        cols = [c['name'] for c in inspector.get_columns(table_name)]
        if column_name not in cols:
            db.session.execute(db.text(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}"))
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f'[MIGRATION WARNING] {table_name}.{column_name}: {e}')


@app.before_request
def setup_db():
    global _db_initialized
    if _db_initialized:
        return
    _db_initialized = True
    try:
        os.makedirs(os.path.join(base_dir, 'instance'), exist_ok=True)
        db.create_all()

        # Bổ sung cột cho database cũ nếu người dùng đang chạy lại trên DB đã có sẵn.
        _add_column_if_missing('users', 'student_id', 'student_id INTEGER NULL')
        _add_column_if_missing('users', 'teacher_id', 'teacher_id INTEGER NULL')
        _add_column_if_missing('users', 'failed_login_count', 'failed_login_count INTEGER DEFAULT 0')
        _add_column_if_missing('users', 'locked_until', 'locked_until DATETIME NULL')
        _add_column_if_missing('users', 'created_at', 'created_at DATETIME')
        _add_column_if_missing('students', 'gender', 'gender VARCHAR(10) NULL')
        _add_column_if_missing('students', 'email', 'email VARCHAR(120) NULL')
        _add_column_if_missing('students', 'phone', 'phone VARCHAR(20) NULL')
        _add_column_if_missing('students', 'class_name', 'class_name VARCHAR(50) NULL')
        _add_column_if_missing('students', 'class_id', 'class_id INTEGER NULL')
        _add_column_if_missing('students', 'date_of_birth', 'date_of_birth DATE NULL')
        _add_column_if_missing('students', 'address', 'address VARCHAR(255) NULL')
        _add_column_if_missing('students', 'department_id', 'department_id INTEGER NULL')
        _add_column_if_missing('students', 'gpa', 'gpa FLOAT DEFAULT 0')
        _add_column_if_missing('students', 'academic_rank', 'academic_rank VARCHAR(20) DEFAULT \'Yếu\'')
        _add_column_if_missing('subjects', 'department_id', 'department_id INTEGER NULL')
        _add_column_if_missing('grades', 'semester_id', 'semester_id INTEGER NULL')

        if not UserModel.query.filter_by(username='admin').first():
            admin = UserModel(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
        if not SemesterModel.query.first():
            sem = SemesterModel(name='Học kỳ 1', academic_year='2024-2025', is_current=True)
            db.session.add(sem)
            db.session.commit()
        current_sem = SemesterModel.query.filter_by(is_current=True).first() or SemesterModel.query.first()
        if current_sem:
            try:
                db.session.execute(db.text('UPDATE grades SET semester_id = :sid WHERE semester_id IS NULL'), {'sid': current_sem.id})
            except Exception:
                pass
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f'[LỖI DATABASE]: {e}')


def generate_jwt_token(username, role):
    payload = {
        'exp': datetime.now(timezone.utc) + timedelta(hours=2),
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
    old_username = ''

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        old_username = username

        user = UserModel.query.filter_by(username=username).first()

        locked, wait = check_brute_force(user)
        if locked:
            flash(f'Tài khoản bị khoá tạm thời. Thử lại sau {wait}.', 'danger')
            return render_template('login.html', old_username=old_username)

        if user and user.check_password(password):
            record_success_login(user)

            session['token'] = generate_jwt_token(user.username, user.role)
            session['username'] = user.username
            session['role'] = user.role
            session['linked_student_id'] = user.student_id
            session['linked_teacher_id'] = user.teacher_id

            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('dashboard'))

        if user:
            record_failed_login(user)

        flash('Tài khoản hoặc mật khẩu không chính xác!', 'danger')
        return render_template('login.html', old_username=old_username)

    return render_template('login.html', old_username=old_username)


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
        flash('Chỉ tài khoản sinh viên mới có trang hồ sơ cá nhân.', 'warning')
        return redirect(url_for('dashboard'))

    linked_student_id = session.get('linked_student_id')

    if not linked_student_id:
        flash('Tài khoản này chưa được liên kết với sinh viên.', 'danger')
        return redirect(url_for('dashboard'))

    student = StudentModel.query.get(linked_student_id)

    if not student:
        flash('Không tìm thấy thông tin sinh viên được liên kết.', 'danger')
        return redirect(url_for('dashboard'))

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
    class_id      = request.args.get('class_id', '')
    page          = request.args.get('page', 1, type=int)

    students, total_pages, total = StudentService.search_students(
        keyword=keyword, gender=gender, rank=rank,
        department_id=department_id, class_id=class_id, page=page
    )
    departments = DepartmentModel.query.order_by(DepartmentModel.department_name).all()
    classes = ClassModel.query.order_by(ClassModel.class_code).all()
    return render_template(
        'students.html',
        students=students, keyword=keyword, gender=gender,
        rank=rank, department_id=department_id, class_id=class_id,
        page=page, total_pages=total_pages, total=total,
        departments=departments, classes=classes,
    )


@app.route('/students/<int:student_id>')
@token_required
@admin_or_self_required
def student_detail(student_id):
    student = StudentModel.query.get_or_404(student_id)
    grades = (GradeModel.query.filter_by(student_id=student_id)
              .join(SubjectModel).join(SemesterModel)
              .order_by(SemesterModel.academic_year.desc(), SemesterModel.name, SubjectModel.subject_name)
              .all())
    user = UserModel.query.filter_by(student_id=student_id).first()
    enrollments = EnrollmentModel.query.filter_by(student_id=student_id).order_by(EnrollmentModel.registered_at.desc()).all()
    return render_template('student_detail.html', student=student, grades=grades, user=user, enrollments=enrollments)


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
        class_id = request.form.get('class_id') or None

        student = StudentModel(
            student_code  = code,
            full_name     = request.form.get('full_name', '').strip(),
            gender        = request.form.get('gender', 'Nam'),
            email         = request.form.get('email', '').strip() or None,
            phone         = request.form.get('phone', '').strip() or None,
            class_name    = request.form.get('class_name', '').strip() or None,
            class_id      = class_id,
            address       = request.form.get('address', '').strip() or None,
            date_of_birth = dob,
            department_id = dept_id,
        )
        db.session.add(student)
        db.session.commit()
        flash(f'Đã thêm sinh viên {student.full_name} thành công!', 'success')
        return redirect(url_for('students_manager'))

    departments = DepartmentModel.query.order_by(DepartmentModel.department_name).all()
    classes = ClassModel.query.order_by(ClassModel.class_code).all()
    return render_template('student_form.html', student=None, action='add',
                           departments=departments, classes=classes)


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
        class_id = request.form.get('class_id') or None

        student.student_code  = code
        student.full_name     = request.form.get('full_name', '').strip()
        student.gender        = request.form.get('gender', 'Nam')
        student.email         = request.form.get('email', '').strip() or None
        student.phone         = request.form.get('phone', '').strip() or None
        student.class_name    = request.form.get('class_name', '').strip() or None
        student.class_id      = class_id
        student.address       = request.form.get('address', '').strip() or None
        student.date_of_birth = dob
        student.department_id = dept_id
        db.session.commit()
        flash('Cập nhật thông tin sinh viên thành công!', 'success')
        return redirect(url_for('students_manager'))

    departments = DepartmentModel.query.order_by(DepartmentModel.department_name).all()
    classes = ClassModel.query.order_by(ClassModel.class_code).all()
    return render_template('student_form.html', student=student, action='edit',
                           departments=departments, classes=classes)


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
                           .filter(~StudentModel.id.in_(db.session.query(UserModel.student_id).filter(UserModel.student_id.isnot(None))))
                           .order_by(StudentModel.full_name).all())
    teachers_no_account = (TeacherModel.query
                           .filter(~TeacherModel.id.in_(db.session.query(UserModel.teacher_id).filter(UserModel.teacher_id.isnot(None))))
                           .order_by(TeacherModel.full_name).all())
    return render_template('users.html', users=users,
                           students_no_account=students_no_account,
                           teachers_no_account=teachers_no_account)


@app.route('/users/add', methods=['POST'])
@token_required
@admin_required
def add_user():
    uname = request.form.get('username', '').strip()
    if UserModel.query.filter_by(username=uname).first():
        flash(f'Tên đăng nhập "{uname}" đã tồn tại!', 'danger')
        return redirect(url_for('users_manager'))
    role = request.form.get('role', 'student')
    user = UserModel(
        username   = uname,
        role       = role,
        student_id = request.form.get('student_id') or None if role == 'student' else None,
        teacher_id = request.form.get('teacher_id') or None if role == 'teacher' else None,
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


# ===================== GIAI ĐOẠN 2: QUẢN LÝ LỚP HỌC =====================
@app.route('/classes')
@token_required
@admin_required
def classes_manager():
    keyword = request.args.get('q', '').strip()
    query = ClassModel.query
    if keyword:
        like = f'%{keyword}%'
        query = query.filter(db.or_(ClassModel.class_code.ilike(like), ClassModel.class_name.ilike(like)))
    classes = query.order_by(ClassModel.class_code).all()
    departments = DepartmentModel.query.order_by(DepartmentModel.department_name).all()
    return render_template('classes.html', classes=classes, departments=departments, keyword=keyword)


@app.route('/classes/add', methods=['POST'])
@token_required
@admin_required
def add_class():
    code = request.form.get('class_code', '').strip()
    name = request.form.get('class_name', '').strip()
    if not code or not name:
        flash('Vui lòng nhập mã lớp và tên lớp!', 'danger')
        return redirect(url_for('classes_manager'))
    if ClassModel.query.filter_by(class_code=code).first():
        flash(f'Mã lớp "{code}" đã tồn tại!', 'danger')
        return redirect(url_for('classes_manager'))
    cls = ClassModel(class_code=code, class_name=name,
                     academic_year=request.form.get('academic_year', '').strip() or None,
                     advisor_name=request.form.get('advisor_name', '').strip() or None,
                     department_id=request.form.get('department_id') or None)
    db.session.add(cls)
    db.session.commit()
    flash('Đã thêm lớp học!', 'success')
    return redirect(url_for('classes_manager'))


@app.route('/classes/<int:class_id>/edit', methods=['POST'])
@token_required
@admin_required
def edit_class(class_id):
    cls = ClassModel.query.get_or_404(class_id)
    cls.class_name = request.form.get('class_name', cls.class_name).strip()
    cls.academic_year = request.form.get('academic_year', '').strip() or None
    cls.advisor_name = request.form.get('advisor_name', '').strip() or None
    cls.department_id = request.form.get('department_id') or None
    db.session.commit()
    flash('Đã cập nhật lớp học!', 'success')
    return redirect(url_for('classes_manager'))


@app.route('/classes/<int:class_id>/delete', methods=['POST'])
@token_required
@admin_required
def delete_class(class_id):
    cls = ClassModel.query.get_or_404(class_id)
    if cls.students:
        flash('Không thể xóa lớp đang có sinh viên!', 'danger')
        return redirect(url_for('classes_manager'))
    db.session.delete(cls)
    db.session.commit()
    flash('Đã xóa lớp học!', 'success')
    return redirect(url_for('classes_manager'))


# ===================== GIAI ĐOẠN 3: GIẢNG VIÊN =====================
@app.route('/teachers')
@token_required
@admin_required
def teachers_manager():
    teachers = TeacherModel.query.order_by(TeacherModel.teacher_code).all()
    departments = DepartmentModel.query.order_by(DepartmentModel.department_name).all()
    return render_template('teachers.html', teachers=teachers, departments=departments)


@app.route('/teachers/add', methods=['POST'])
@token_required
@admin_required
def add_teacher():
    code = request.form.get('teacher_code', '').strip()
    name = request.form.get('full_name', '').strip()
    if not code or not name:
        flash('Vui lòng nhập mã giảng viên và họ tên!', 'danger')
        return redirect(url_for('teachers_manager'))
    if TeacherModel.query.filter_by(teacher_code=code).first():
        flash(f'Mã giảng viên "{code}" đã tồn tại!', 'danger')
        return redirect(url_for('teachers_manager'))
    teacher = TeacherModel(teacher_code=code, full_name=name,
                           email=request.form.get('email', '').strip() or None,
                           phone=request.form.get('phone', '').strip() or None,
                           department_id=request.form.get('department_id') or None)
    db.session.add(teacher)
    db.session.commit()
    flash('Đã thêm giảng viên!', 'success')
    return redirect(url_for('teachers_manager'))


@app.route('/teachers/<int:teacher_id>/delete', methods=['POST'])
@token_required
@admin_required
def delete_teacher(teacher_id):
    teacher = TeacherModel.query.get_or_404(teacher_id)
    if teacher.sections:
        flash('Không thể xóa giảng viên đang được phân công lớp học phần!', 'danger')
        return redirect(url_for('teachers_manager'))
    db.session.delete(teacher)
    db.session.commit()
    flash('Đã xóa giảng viên!', 'success')
    return redirect(url_for('teachers_manager'))


# ===================== GIAI ĐOẠN 3: LỚP HỌC PHẦN =====================
@app.route('/course-sections')
@token_required
@admin_required
def course_sections_manager():
    sections = CourseSectionModel.query.order_by(CourseSectionModel.section_code).all()
    subjects = SubjectModel.query.order_by(SubjectModel.subject_name).all()
    semesters = SemesterModel.query.order_by(SemesterModel.academic_year.desc(), SemesterModel.name).all()
    teachers = TeacherModel.query.order_by(TeacherModel.full_name).all()
    return render_template('course_sections.html', sections=sections, subjects=subjects, semesters=semesters, teachers=teachers)


@app.route('/course-sections/add', methods=['POST'])
@token_required
@admin_required
def add_course_section():
    code = request.form.get('section_code', '').strip()
    if not code:
        flash('Vui lòng nhập mã lớp học phần!', 'danger')
        return redirect(url_for('course_sections_manager'))
    if CourseSectionModel.query.filter_by(section_code=code).first():
        flash(f'Mã lớp học phần "{code}" đã tồn tại!', 'danger')
        return redirect(url_for('course_sections_manager'))
    section = CourseSectionModel(section_code=code,
                                 subject_id=request.form.get('subject_id'),
                                 semester_id=request.form.get('semester_id'),
                                 teacher_id=request.form.get('teacher_id') or None,
                                 max_students=request.form.get('max_students', type=int) or 50,
                                 room=request.form.get('room', '').strip() or None,
                                 schedule=request.form.get('schedule', '').strip() or None,
                                 status=request.form.get('status', 'open'))
    db.session.add(section)
    db.session.commit()
    flash('Đã thêm lớp học phần!', 'success')
    return redirect(url_for('course_sections_manager'))


@app.route('/course-sections/<int:section_id>/delete', methods=['POST'])
@token_required
@admin_required
def delete_course_section(section_id):
    section = CourseSectionModel.query.get_or_404(section_id)
    if section.enrollments:
        flash('Không thể xóa lớp học phần đã có sinh viên đăng ký!', 'danger')
        return redirect(url_for('course_sections_manager'))
    db.session.delete(section)
    db.session.commit()
    flash('Đã xóa lớp học phần!', 'success')
    return redirect(url_for('course_sections_manager'))


@app.route('/course-sections/<int:section_id>/toggle_lock', methods=['POST'])
@token_required
@admin_required
def toggle_section_lock(section_id):
    section = CourseSectionModel.query.get_or_404(section_id)
    section.grades_locked = not section.grades_locked
    if section.grades_locked:
        section.status = 'locked'
    db.session.commit()
    flash('Đã cập nhật trạng thái khóa điểm!', 'success')
    return redirect(url_for('course_sections_manager'))


# ===================== ĐĂNG KÝ HỌC PHẦN =====================
@app.route('/enrollments')
@token_required
def enrollments_page():
    sections = CourseSectionModel.query.order_by(CourseSectionModel.section_code).all()
    user = UserModel.query.filter_by(username=session.get('username')).first()
    my_enrollments = []
    registered_section_ids = set()
    if user and user.student_id:
        my_enrollments = EnrollmentModel.query.filter_by(student_id=user.student_id).all()
        registered_section_ids = {e.section_id for e in my_enrollments if e.status == 'registered'}
    return render_template('enrollments.html', sections=sections, my_enrollments=my_enrollments, registered_section_ids=registered_section_ids)


@app.route('/enrollments/register/<int:section_id>', methods=['POST'])
@token_required
def register_section(section_id):
    if session.get('role') != 'student':
        abort(403)
    user = UserModel.query.filter_by(username=session.get('username')).first()
    if not user or not user.student_id:
        flash('Tài khoản chưa liên kết sinh viên!', 'danger')
        return redirect(url_for('enrollments_page'))
    section = CourseSectionModel.query.get_or_404(section_id)
    if section.status != 'open':
        flash('Lớp học phần này chưa mở đăng ký hoặc đã đóng!', 'danger')
        return redirect(url_for('enrollments_page'))
    if section.is_full:
        flash('Lớp học phần đã đủ sĩ số!', 'danger')
        return redirect(url_for('enrollments_page'))
    existed = EnrollmentModel.query.filter_by(student_id=user.student_id, section_id=section_id).first()
    if existed:
        if existed.status != 'registered':
            existed.status = 'registered'
            db.session.commit()
            flash('Đã đăng ký lại học phần!', 'success')
        else:
            flash('Bạn đã đăng ký lớp học phần này rồi!', 'warning')
        return redirect(url_for('enrollments_page'))
    enrollment = EnrollmentModel(student_id=user.student_id, section_id=section_id)
    db.session.add(enrollment)
    db.session.commit()
    flash('Đăng ký học phần thành công!', 'success')
    return redirect(url_for('enrollments_page'))


@app.route('/enrollments/cancel/<int:enrollment_id>', methods=['POST'])
@token_required
def cancel_enrollment(enrollment_id):
    if session.get('role') != 'student':
        abort(403)
    user = UserModel.query.filter_by(username=session.get('username')).first()
    enrollment = EnrollmentModel.query.get_or_404(enrollment_id)
    if not user or enrollment.student_id != user.student_id:
        abort(403)
    if enrollment.section.status != 'open':
        flash('Không thể hủy vì lớp học phần đã đóng đăng ký!', 'danger')
        return redirect(url_for('enrollments_page'))
    db.session.delete(enrollment)
    db.session.commit()
    flash('Đã hủy đăng ký học phần!', 'success')
    return redirect(url_for('enrollments_page'))


# ===================== GIẢNG VIÊN NHẬP ĐIỂM =====================
@app.route('/teacher/sections')
@token_required
@admin_or_teacher_required
def teacher_sections():
    user = UserModel.query.filter_by(username=session.get('username')).first()
    if session.get('role') == 'admin':
        sections = CourseSectionModel.query.order_by(CourseSectionModel.section_code).all()
    else:
        sections = CourseSectionModel.query.filter_by(teacher_id=user.teacher_id).order_by(CourseSectionModel.section_code).all()
    return render_template('teacher_sections.html', sections=sections)


@app.route('/teacher/sections/<int:section_id>/grades', methods=['GET', 'POST'])
@token_required
@admin_or_teacher_required
def section_grades(section_id):
    section = CourseSectionModel.query.get_or_404(section_id)
    user = UserModel.query.filter_by(username=session.get('username')).first()
    if session.get('role') == 'teacher' and section.teacher_id != user.teacher_id:
        abort(403)
    enrollments = EnrollmentModel.query.filter_by(section_id=section_id, status='registered').all()
    if request.method == 'POST':
        if section.grades_locked and session.get('role') != 'admin':
            flash('Điểm lớp này đã bị khóa. Vui lòng liên hệ admin.', 'danger')
            return redirect(request.url)
        for e in enrollments:
            pg = request.form.get(f'progress_{e.student_id}', type=float)
            eg = request.form.get(f'exam_{e.student_id}', type=float)
            if pg is None or eg is None:
                continue
            if not (0 <= pg <= 10 and 0 <= eg <= 10):
                flash('Điểm phải nằm trong khoảng 0 đến 10!', 'danger')
                return redirect(request.url)
            StudentService.upsert_grade(e.student_id, section.subject_id, section.semester_id, pg, eg, actor=session.get('username', 'teacher'))
        flash('Đã lưu điểm lớp học phần!', 'success')
        return redirect(request.url)
    grade_map = {}
    for e in enrollments:
        grade_map[e.student_id] = GradeModel.query.filter_by(student_id=e.student_id, subject_id=section.subject_id, semester_id=section.semester_id).first()
    return render_template('section_grades.html', section=section, enrollments=enrollments, grade_map=grade_map)



# ===================== THỜI KHÓA BIỂU KIỂU LƯỚI TUẦN =====================

WEEKDAY_MAP = {
    2: 'Thứ 2',
    3: 'Thứ 3',
    4: 'Thứ 4',
    5: 'Thứ 5',
    6: 'Thứ 6',
    7: 'Thứ 7',
    8: 'Chủ nhật'
}


def parse_schedule_text(schedule_text):
    """
    Hỗ trợ các dạng nhập lịch:
    - Thứ 2 - 06:45 - 09:25
    - T2 06:45-09:25
    - Thứ 4 | 09:30 | 12:10
    - Thứ 6 - Tiết 1-3 - 06:45-09:25
    """
    if not schedule_text:
        return None

    text = schedule_text.strip().lower()
    weekday = None

    if 'thứ 2' in text or 'thu 2' in text or re.search(r'\bt2\b', text):
        weekday = 2
    elif 'thứ 3' in text or 'thu 3' in text or re.search(r'\bt3\b', text):
        weekday = 3
    elif 'thứ 4' in text or 'thu 4' in text or re.search(r'\bt4\b', text):
        weekday = 4
    elif 'thứ 5' in text or 'thu 5' in text or re.search(r'\bt5\b', text):
        weekday = 5
    elif 'thứ 6' in text or 'thu 6' in text or re.search(r'\bt6\b', text):
        weekday = 6
    elif 'thứ 7' in text or 'thu 7' in text or re.search(r'\bt7\b', text):
        weekday = 7
    elif 'chủ nhật' in text or 'chu nhat' in text or re.search(r'\bcn\b', text):
        weekday = 8

    time_matches = re.findall(r'(\d{1,2}:\d{2})', schedule_text)

    if len(time_matches) >= 2:
        start_time = time_matches[0]
        end_time = time_matches[1]
    else:
        start_time = '07:00'
        end_time = '09:00'

    return {
        'weekday': weekday,
        'start_time': start_time,
        'end_time': end_time
    }


def time_to_minutes(time_text):
    hour, minute = map(int, time_text.split(':'))
    return hour * 60 + minute


def get_week_start(any_date=None):
    if any_date is None:
        any_date = datetime.today().date()
    return any_date - timedelta(days=any_date.weekday())


def build_week_days(base_date=None):
    week_start = get_week_start(base_date)
    days = []

    for i in range(7):
        current_date = week_start + timedelta(days=i)
        weekday_num = i + 2 if i < 6 else 8
        days.append({
            'index': i,
            'date': current_date,
            'label': WEEKDAY_MAP[weekday_num],
            'weekday_num': weekday_num
        })

    return days


def build_timetable_events(sections):
    events = []
    colors = ['primary', 'orange', 'purple', 'success', 'danger', 'info', 'secondary']

    for index, section in enumerate(sections):
        parsed = parse_schedule_text(section.schedule or '')

        if not parsed or not parsed.get('weekday'):
            continue

        weekday_num = parsed['weekday']
        start_time = parsed['start_time']
        end_time = parsed['end_time']

        start_minutes = time_to_minutes(start_time)
        end_minutes = time_to_minutes(end_time)

        day_index = 6 if weekday_num == 8 else weekday_num - 2

        events.append({
            'id': section.id,
            'section_code': section.section_code,
            'subject_name': section.subject.subject_name if section.subject else f'Môn {section.subject_id}',
            'teacher_name': section.teacher.full_name if section.teacher else 'Chưa phân công',
            'room': section.room or 'Chưa có phòng',
            'schedule_text': section.schedule or 'Chưa nhập lịch',
            'status': section.status or 'open',
            'start_time': start_time,
            'end_time': end_time,
            'start_minutes': start_minutes,
            'end_minutes': end_minutes,
            'duration_minutes': max(45, end_minutes - start_minutes),
            'day_index': day_index,
            'color_class': colors[index % len(colors)]
        })

    return events


def build_event_students(sections):
    event_id_to_students = {}

    for section in sections:
        students = []
        for enrollment in section.enrollments:
            if enrollment.status == 'registered' and enrollment.student:
                students.append(enrollment.student)
        event_id_to_students[section.id] = students

    return event_id_to_students


@app.route('/timetable')
@token_required
def timetable_redirect():
    if session.get('role') == 'student':
        return redirect(url_for('student_timetable'))

    if session.get('role') == 'teacher':
        return redirect(url_for('teacher_timetable'))

    return redirect(url_for('admin_timetable'))


@app.route('/student/timetable')
@token_required
def student_timetable():
    if session.get('role') not in ['student', 'admin']:
        abort(403)

    user = UserModel.query.filter_by(username=session.get('username')).first()

    if session.get('role') == 'admin':
        sections = CourseSectionModel.query.order_by(CourseSectionModel.section_code).all()
        page_title = 'Thời khóa biểu sinh viên'
        page_note = 'Admin đang xem toàn bộ lịch học.'
    else:
        if not user or not user.student_id:
            flash('Tài khoản sinh viên chưa được liên kết với thông tin sinh viên.', 'warning')
            sections = []
        else:
            enrollments = (
                EnrollmentModel.query
                .filter_by(student_id=user.student_id, status='registered')
                .all()
            )
            sections = [e.section for e in enrollments if e.section]

        page_title = 'Lịch học'
        page_note = 'Thời khóa biểu cá nhân của sinh viên.'

    week_days = build_week_days()
    events = build_timetable_events(sections)
    event_id_to_students = {}

    return render_template(
        'timetable.html',
        page_title=page_title,
        page_note=page_note,
        timetable_type='student',
        week_days=week_days,
        events=events,
        event_id_to_students=event_id_to_students
    )


@app.route('/teacher/timetable')
@token_required
def teacher_timetable():
    if session.get('role') not in ['teacher', 'admin']:
        abort(403)

    user = UserModel.query.filter_by(username=session.get('username')).first()

    if session.get('role') == 'admin':
        sections = CourseSectionModel.query.order_by(CourseSectionModel.section_code).all()
        page_title = 'Thời khóa biểu giảng viên'
        page_note = 'Admin đang xem toàn bộ lịch giảng dạy.'
    else:
        if not user or not user.teacher_id:
            flash('Tài khoản giảng viên chưa được liên kết với thông tin giảng viên.', 'warning')
            sections = []
        else:
            sections = (
                CourseSectionModel.query
                .filter_by(teacher_id=user.teacher_id)
                .order_by(CourseSectionModel.section_code)
                .all()
            )

        page_title = 'Lịch dạy'
        page_note = 'Thời khóa biểu giảng dạy của giảng viên.'

    week_days = build_week_days()
    events = build_timetable_events(sections)
    event_id_to_students = build_event_students(sections)

    return render_template(
        'timetable.html',
        page_title=page_title,
        page_note=page_note,
        timetable_type='teacher',
        week_days=week_days,
        events=events,
        event_id_to_students=event_id_to_students
    )


@app.route('/admin/timetable')
@token_required
@admin_required
def admin_timetable():
    sections = CourseSectionModel.query.order_by(CourseSectionModel.section_code).all()

    week_days = build_week_days()
    events = build_timetable_events(sections)
    event_id_to_students = build_event_students(sections)

    return render_template(
        'timetable.html',
        page_title='Thời khóa biểu toàn hệ thống',
        page_note='Admin xem toàn bộ lịch học và lịch dạy.',
        timetable_type='admin',
        week_days=week_days,
        events=events,
        event_id_to_students=event_id_to_students
    )


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
    temp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    temp.close()
    StudentService.export_students_to_excel(temp.name, semester_id=sem_id)
    return send_file(temp.name, as_attachment=True, download_name='baocao_sinhvien.xlsx')


if __name__ == '__main__':
    os.makedirs(os.path.join(base_dir, 'instance'), exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=False)