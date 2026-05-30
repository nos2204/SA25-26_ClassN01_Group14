# gateway.py  —  API Gateway: kiểm soát xác thực & phân quyền
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import jwt
from functools import wraps
from flask import session, flash, redirect, url_for, request


# ------------------------------------------------------------------ #
#  Lớp 1: Yêu cầu đăng nhập hợp lệ (kiểm tra JWT trong session)     #
# ------------------------------------------------------------------ #
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = session.get('token')
        if not token:
            flash('Chưa đăng nhập hoặc phiên làm việc đã hết hạn!', 'danger')
            return redirect(url_for('login'))
        try:
            secret = os.getenv('FLASK_SECRET_KEY', 'quanlidiemsinhvien_secret_key_2026')
            data   = jwt.decode(token, secret, algorithms=['HS256'])
            request.user_data = data
        except jwt.ExpiredSignatureError:
            session.clear()
            flash('Mã xác thực token đã hết hạn, vui lòng đăng nhập lại!', 'danger')
            return redirect(url_for('login'))
        except jwt.InvalidTokenError:
            session.clear()
            flash('Token không hợp lệ!', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ------------------------------------------------------------------ #
#  Lớp 2: Chỉ Admin mới được thực hiện                               #
#  CÁCH DÙNG ĐÚNG: đặt @admin_required SAU @app.route trên route     #
# ------------------------------------------------------------------ #
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Phải đã qua token_required trước (role nằm trong session)
        if session.get('role') != 'admin':
            flash('Chỉ tài khoản Admin mới được thực hiện chức năng này!', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


# ------------------------------------------------------------------ #
#  Lớp 3: Admin hoặc chính sinh viên đó mới được xem                 #
# ------------------------------------------------------------------ #
def admin_or_self_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') == 'admin':
            return f(*args, **kwargs)
        # Sinh viên chỉ xem được hồ sơ của mình
        target_id = kwargs.get('student_id')
        if target_id and str(session.get('linked_student_id')) == str(target_id):
            return f(*args, **kwargs)
        flash('Bạn không có quyền truy cập tài nguyên này!', 'danger')
        return redirect(url_for('dashboard'))
    return decorated