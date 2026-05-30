import os
import sys

# Lấy đường dẫn tuyệt đối của thư mục chứa file app.py này và ép vào bộ nhớ Python
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# =========================================================================
# 2. KHAI BÁO CÁC THƯ VIỆN HỆ THỐNG VÀ THƯ VIỆN BÊN THỨ BA
# =========================================================================
import jwt
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from dotenv import load_dotenv

# Nạp các thành phần từ mô hình 3 tầng độc lập của dự án
from persistence.models import db, UserModel, StudentModel
from business.student_service import StudentService
from gateway import token_required, admin_required  # Bộ lọc kiểm soát của API Gateway

# Tải cấu hình biến môi trường từ file .env theo đường dẫn tuyệt đối ổn định
base_dir = os.path.dirname(os.path.abspath(__file__))
# Tìm file .env ở thư mục hiện tại, nếu không có sẽ lùi ra thư mục cha ngoài cùng
env_path = os.path.join(base_dir, '.env') if os.path.exists(os.path.join(base_dir, '.env')) else os.path.join(os.path.dirname(base_dir), '.env')
load_dotenv(env_path)

# =========================================================================
# 3. KHỞI TẠO VÀ CẤU HÌNH ỨNG DỤNG FLASK CÙNG MYSQL
# =========================================================================
app = Flask(__name__, template_folder='presentation/templates', static_folder='presentation/static')

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'quanlidiemsinhvien_secret_key_2026')

# Thiết lập cấu hình kết nối linh hoạt, tự động fallback nếu biến môi trường trống
db_user = os.getenv('DB_USER', 'root')
db_password = os.getenv('DB_PASSWORD', '')
db_host = os.getenv('DB_HOST', 'localhost')
db_name = os.getenv('DB_NAME', 'quanlidiemsinhvien')

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Gắn kết database vào Flask
db.init_app(app)

# Hàm bổ trợ: Tự động tạo chuỗi mã hóa bảo mật Token JWT có thời hạn 2 giờ
def generate_jwt_token(username, role):
    payload = {
        'exp': datetime.utcnow() + timedelta(hours=2),
        'sub': username,
        'role': role
    }
    return jwt.encode(payload, app.secret_key, algorithm='HS256')

# =========================================================================
# 4. TỰ ĐỘNG KHỞI TẠO CƠ SỞ DỮ LIỆU VÀ TÀI KHOẢN ADMIN MẶC ĐỊNH
# =========================================================================
@app.before_request
def setup_db():
    # Gỡ bỏ hàm khỏi danh sách chạy sau lần gọi đầu tiên để tối ưu hiệu năng
    if setup_db in app.before_request_funcs.get(None, []):
        app.before_request_funcs[None].remove(setup_db)
    
    try:
        # Tự tạo bảng tự động dựa trên cấu trúc mô hình models.py
        db.create_all()
        
        # Khởi tạo tài khoản quản trị viên tối cao ban đầu nếu database trống
        if not UserModel.query.filter_by(username="admin").first():
            admin = UserModel(username="admin", role="admin")
            admin.set_password("admin123")  # Băm mật khẩu bảo mật trước khi lưu
            db.session.add(admin)
            db.session.commit()
    except Exception as e:
        print(f"====== [LỖI KẾT NỐI DATABASE]: Môi trường chưa khởi tạo cấu hình MySQL hoàn chỉnh. Chi tiết: {e} ======")

# =========================================================================
# 5. ĐỊNH TUYẾN CÁC ENDPOINTS URL (CONTROLLER LAYER)
# =========================================================================

# Trang đăng nhập xác thực tài khoản hệ thống (ĐÃ SỬA LỖI TRẢ VỀ CHO PHƯƠNG THỨC GET)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = UserModel.query.filter_by(username=username).first()
        if user and user.check_password(password):
            # Tạo Token JWT thực tế đẩy vào Session làm việc
            session['token'] = generate_jwt_token(user.username, user.role)
            session['username'] = user.username
            session['role'] = user.role
            flash("Xác thực cổng Gateway và Đăng nhập thành công!", "success")
            return redirect(url_for('dashboard'))
        
        flash("Tài khoản hoặc mật khẩu không chính xác.", "danger")
    
    # Đảm bảo phương thức GET luôn trả về giao diện trang login công khai
    return render_template('login.html')

# Trang chủ thống kê - Bắt buộc đi qua cổng kiểm duyệt API Gateway số 1
@app.route('/')
@token_required
def dashboard():
    total_stu = StudentModel.query.count()
    gioi_stu = StudentModel.query.filter_by(academic_rank="Giỏi").count()
    return render_template('dashboard.html', total=total_stu, gioi=gioi_stu)

# Hàm bổ trợ thêm sinh viên (được bọc bởi decorator kiểm tra quyền admin một cách tường minh)
@admin_required
def perform_add_student():
    new_stu = StudentModel(
        student_code=request.form.get('student_code'),
        full_name=request.form.get('full_name'),
        gender=request.form.get('gender')
    )
    db.session.add(new_stu)
    db.session.commit()
    flash("Thêm hồ sơ sinh viên mới vào MySQL thành công!", "success")

# Trang quản lý danh sách Sinh viên - Tích hợp phân quyền API Gateway lớp 2
@app.route('/students', methods=['GET', 'POST'])
@token_required
def students_manager():
    if request.method == 'POST':
        perform_add_student()
        return redirect(url_for('students_manager'))
        
    students = StudentModel.query.all()
    return render_template('students.html', students=students)

# Endpoint kết xuất báo cáo học tập định dạng tệp Excel từ Tầng Business
@app.route('/export')
@token_required
def export_excel():
    path = "baocao_sinhvien.xlsx"
    StudentService.export_students_to_excel(path)
    return send_file(path, as_attachment=True)

# Hủy phiên làm việc, xóa sạch Token JWT
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Kích hoạt chạy Server máy chủ ở chế độ phát triển
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)