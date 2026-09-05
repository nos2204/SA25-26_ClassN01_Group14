# student_grade_system/blueprints/auth.py
import jwt
import os
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from persistence.models import db, UserModel
from gateway import (token_required, check_brute_force,
                     record_failed_login, record_success_login)

auth_bp = Blueprint('auth', __name__)


def generate_jwt_token(username, role):
    payload = {
        'exp': datetime.now(timezone.utc) + timedelta(hours=2),
        'sub': username,
        'role': role,
    }
    secret = current_app.config.get('SECRET_KEY') or os.getenv('FLASK_SECRET_KEY', 'quanlidiemsinhvien_secret_key_2026')
    return jwt.encode(payload, secret, algorithm='HS256')


@auth_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = UserModel.query.filter_by(username=username).first()

        is_locked, lock_msg = check_brute_force(user)
        if is_locked:
            flash(f'Tài khoản bị khóa do nhập sai quá 5 lần. Thử lại sau {lock_msg}!', 'danger')
            return render_template('login.html')

        if user and user.check_password(password):
            record_success_login(user)
            token = generate_jwt_token(username, user.role)
            session['token'] = token
            session['username'] = user.username
            session['role'] = user.role
            session['user_id'] = user.id
            session['student_id'] = user.student_id
            session['teacher_id'] = user.teacher_id
            session['linked_student_id'] = user.student_id
            flash(f'Đăng nhập thành công! Xin chào {user.username}', 'success')
            return redirect(url_for('dashboard'))

        if user:
            record_failed_login(user)
        flash('Tên đăng nhập hoặc mật khẩu không chính xác!', 'danger')
    return render_template('login.html')


@auth_bp.route('/logout', endpoint='logout')
def logout():
    session.clear()
    flash('Đã đăng xuất thành công!', 'info')
    return redirect(url_for('login'))


@auth_bp.route('/change_password', methods=['GET', 'POST'], endpoint='change_password')
@token_required
def change_password():
    if request.method == 'POST':
        user = UserModel.query.filter_by(username=session['username']).first()
        old_pass = request.form.get('old_password', '')
        new_pass = request.form.get('new_password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()
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
