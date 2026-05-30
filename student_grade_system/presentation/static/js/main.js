document.addEventListener('DOMContentLoaded', function () {

    document.querySelectorAll('.alert.alert-dismissible').forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // 2. Validate form thêm/sửa sinh viên
    const studentForm = document.querySelector('form[action*="student"]');
    if (studentForm) {
        studentForm.addEventListener('submit', function (e) {
            const codeInput = document.querySelector('input[name="student_code"]');
            const nameInput = document.querySelector('input[name="full_name"]');
            const phoneInput = document.querySelector('input[name="phone"]');

            if (codeInput && codeInput.value.trim().length < 3) {
                alert('MSSV phải có ít nhất 3 ký tự!');
                e.preventDefault(); return;
            }
            if (nameInput && /\d/.test(nameInput.value)) {
                alert('Họ và tên không được chứa chữ số!');
                e.preventDefault(); return;
            }
            if (phoneInput && phoneInput.value && !/^[0-9\+\-\s]{9,15}$/.test(phoneInput.value.trim())) {
                alert('Số điện thoại không hợp lệ!');
                e.preventDefault(); return;
            }
        });
    }

    // 3. Validate điểm: chỉ nhập 0–10
    document.querySelectorAll('.grade-input').forEach(function (input) {
        input.addEventListener('change', function () {
            const val = parseFloat(this.value);
            if (isNaN(val) || val < 0 || val > 10) {
                this.classList.add('is-invalid');
                this.title = 'Điểm phải từ 0 đến 10';
            } else {
                this.classList.remove('is-invalid');
                this.title = '';
            }
        });
    });

    // 4. Tooltip Bootstrap
    document.querySelectorAll('[title]').forEach(function (el) {
        new bootstrap.Tooltip(el, { trigger: 'hover' });
    });

});