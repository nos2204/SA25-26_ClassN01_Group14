import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path: sys.path.insert(0, current_dir)
import jwt
from functools import wraps
from flask import session, flash, redirect, url_for, request

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = session.get('token')
        if not token:
            flash("API Gateway thông báo: Chưa đăng nhập hoặc hết phiên làm việc!", "danger")
            return redirect(url_for('login'))
        try:
            # Giải mã Token bằng khóa bí mật bí mật
            data = jwt.decode(token, os.getenv('FLASK_SECRET_KEY'), algorithms=['HS256'])
            request.user_data = data
        except jwt.ExpiredSignatureError:
            session.clear()
            flash("Mã xác thực token đã hết hạn!", "danger")
            return redirect(url_for('login'))
        except jwt.InvalidTokenError:
            session.clear()
            flash("Mã xác thực không hợp lệ!", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# Lớp gác cổng số 2: Chặn đứng nếu tài khoản không phải quyền 'admin'
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("API Gateway từ chối: Chỉ tài khoản Admin mới được thực hiện chức năng này!", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated