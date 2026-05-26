# app.py
import json
import os
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Đường dẫn file để lưu trữ dữ liệu (Persistence)
DB_FILE = 'students_data.json'

def load_db():
    """Tải dữ liệu từ file JSON, nếu chưa có thì tạo mới danh sách rỗng."""
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(data):
    """Lưu danh sách sinh viên vào file JSON."""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Giao diện HTML hiện đại sử dụng Bootstrap 5
HTML_INTERFACE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hệ thống Quản lý Sinh viên Hoàn chỉnh</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background-color: #f8f9fa; }
        .navbar { background-color: #004085; }
        .card-header { font-weight: bold; text-transform: uppercase; }
        .btn-action { padding: 0.25rem 0.5rem; font-size: 0.875rem; }
    </style>
</head>
<body>

<nav class="navbar navbar-dark mb-4">
    <div class="container">
        <a class="navbar-brand" href="#"><i class="fas fa-user-graduate me-2"></i>HỆ THỐNG QUẢN LÝ SINH VIÊN</a>
    </div>
</nav>

<div class="container">
    <div class="row">
        <div class="col-md-4">
            <div class="card shadow-sm border-0">
                <div class="card-header bg-primary text-white">
                    <span id="formTitle">Thêm Sinh Viên Mới</span>
                </div>
                <div class="card-body">
                    <form id="studentForm">
                        <input type="hidden" id="edit_index" value="-1">
                        <div class="mb-3">
                            <label class="form-label">Mã Sinh Viên</label>
                            <input type="text" id="student_id" class="form-control" placeholder="SV001" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Họ và Tên</label>
                            <input type="text" id="name" class="form-control" placeholder="Nguyễn Văn A" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Giới Tính</label>
                            <select id="gender" class="form-select">
                                <option value="Nam">Nam</option>
                                <option value="Nữ">Nữ</option>
                                <option value="Khác">Khác</option>
                            </select>
                        </div>
                        <button type="submit" id="submitBtn" class="btn btn-success w-100">
                            <i class="fas fa-save me-2"></i>Lưu Thông Tin
                        </button>
                        <button type="button" id="cancelBtn" class="btn btn-secondary w-100 mt-2 d-none" onclick="resetForm()">
                            Hủy chỉnh sửa
                        </button>
                    </form>
                </div>
            </div>
        </div>

        <div class="col-md-8">
            <div class="card shadow-sm border-0">
                <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                    DANH SÁCH SINH VIÊN
                    <div class="input-group input-group-sm w-50">
                        <input type="text" id="searchInput" class="form-control" placeholder="Tìm theo tên hoặc mã...">
                        <button class="btn btn-outline-light" type="button" onclick="loadStudents()"><i class="fas fa-search"></i></button>
                    </div>
                </div>
                <div class="card-body p-0">
                    <table class="table table-hover mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Mã SV</th>
                                <th>Họ Tên</th>
                                <th>Giới Tính</th>
                                <th class="text-center">Hành động</th>
                            </tr>
                        </thead>
                        <tbody id="studentTableBody">
                            </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

<script>
    const apiBase = '/api/students';

    // 1. Tải danh sách sinh viên
    async function loadStudents() {
        const search = document.getElementById('searchInput').value;
        const response = await fetch(`${apiBase}?search=${encodeURIComponent(search)}`);
        const students = await response.json();
        
        const tbody = document.getElementById('studentTableBody');
        tbody.innerHTML = '';
        
        students.forEach((sv, index) => {
            tbody.innerHTML += `
                <tr>
                    <td><strong>${sv.student_id}</strong></td>
                    <td>${sv.name}</td>
                    <td>${sv.gender}</td>
                    <td class="text-center">
                        <button class="btn btn-warning btn-action me-1" onclick="editStudent(${index})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-danger btn-action" onclick="deleteStudent(${index})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
    }

    // 2. Xử lý gửi Form (Thêm hoặc Cập nhật)
    document.getElementById('studentForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const editIndex = parseInt(document.getElementById('edit_index').value);
        const student = {
            student_id: document.getElementById('student_id').value,
            name: document.getElementById('name').value,
            gender: document.getElementById('gender').value
        };

        const method = editIndex === -1 ? 'POST' : 'PUT';
        const url = editIndex === -1 ? apiBase : `${apiBase}/${editIndex}`;

        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(student)
        });

        if (response.ok) {
            resetForm();
            loadStudents();
        }
    });

    // 3. Xóa sinh viên
    async function deleteStudent(index) {
        if (confirm('Bạn có chắc chắn muốn xóa sinh viên này?')) {
            await fetch(`${apiBase}/${index}`, { method: 'DELETE' });
            loadStudents();
        }
    }

    // 4. Chuẩn bị chỉnh sửa
    async function editStudent(index) {
        const response = await fetch(apiBase);
        const students = await response.json();
        const sv = students[index];

        document.getElementById('student_id').value = sv.student_id;
        document.getElementById('name').value = sv.name;
        document.getElementById('gender').value = sv.gender;
        document.getElementById('edit_index').value = index;

        document.getElementById('formTitle').innerText = 'Chỉnh sửa sinh viên';
        document.getElementById('submitBtn').classList.replace('btn-success', 'btn-warning');
        document.getElementById('cancelBtn').classList.remove('d-none');
    }

    function resetForm() {
        document.getElementById('studentForm').reset();
        document.getElementById('edit_index').value = "-1";
        document.getElementById('formTitle').innerText = 'Thêm Sinh Viên Mới';
        document.getElementById('submitBtn').classList.replace('btn-warning', 'btn-success');
        document.getElementById('cancelBtn').classList.add('d-none');
    }

    // Tải dữ liệu ban đầu
    loadStudents();
</script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_INTERFACE)

# API: Lấy danh sách (Có chức năng tìm kiếm)
@app.route('/api/students', methods=['GET'])
def get_students():
    db = load_db()
    search = request.args.get('search', '').lower()
    if search:
        db = [s for s in db if search in s['name'].lower() or search in s['student_id'].lower()]
    return jsonify(db)

# API: Thêm mới
@app.route('/api/students', methods=['POST'])
def add_student():
    db = load_db()
    db.append(request.json)
    save_db(db)
    return jsonify({'status': 'ok'}), 201

# API: Cập nhật
@app.route('/api/students/<int:index>', methods=['PUT'])
def update_student(index):
    db = load_db()
    if 0 <= index < len(db):
        db[index] = request.json
        save_db(db)
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'Not found'}), 404

# API: Xóa
@app.route('/api/students/<int:index>', methods=['DELETE'])
def delete_student(index):
    db = load_db()
    if 0 <= index < len(db):
        db.pop(index)
        save_db(db)
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'Not found'}), 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)