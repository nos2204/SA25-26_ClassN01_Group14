document.addEventListener('DOMContentLoaded', function () {

    document.querySelectorAll('.alert.alert-dismissible').forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    const originalFetch = window.fetch;
    window.fetch = function (url, options = {}) {
        options.headers = options.headers || {};
        if (!options.headers['X-CSRF-Token']) {
            options.headers['X-CSRF-Token'] = getCsrfToken();
        }
        return originalFetch(url, options);
    };

    const studentForm = document.querySelector('form[action*="student"]');
    if (studentForm) {
        studentForm.addEventListener('submit', function (e) {
            const codeInput  = studentForm.querySelector('input[name="student_code"]');
            const nameInput  = studentForm.querySelector('input[name="full_name"]');
            const phoneInput = studentForm.querySelector('input[name="phone"]');
            const emailInput = studentForm.querySelector('input[name="email"]');

            if (codeInput && codeInput.value.trim().length < 3) {
                showValidationError(codeInput, 'MSSV phải có ít nhất 3 ký tự!');
                e.preventDefault(); return;
            }
            if (nameInput && /\d/.test(nameInput.value)) {
                showValidationError(nameInput, 'Họ và tên không được chứa chữ số!');
                e.preventDefault(); return;
            }
            if (phoneInput && phoneInput.value && !/^[0-9+\-\s]{9,15}$/.test(phoneInput.value.trim())) {
                showValidationError(phoneInput, 'Số điện thoại không hợp lệ (9–15 ký tự số)!');
                e.preventDefault(); return;
            }
            if (emailInput && emailInput.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailInput.value.trim())) {
                showValidationError(emailInput, 'Địa chỉ email không hợp lệ!');
                e.preventDefault(); return;
            }
        });
    }

    function showValidationError(input, message) {
        input.classList.add('is-invalid');
        let feedback = input.nextElementSibling;
        if (!feedback || !feedback.classList.contains('invalid-feedback')) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            input.after(feedback);
        }
        feedback.textContent = message;
        input.focus();
        input.addEventListener('input', function () {
            input.classList.remove('is-invalid');
        }, { once: true });
    }

    function calcFinalForRow(row) {
        const pgInput = row.querySelector('input[name^="progress_"]');
        const egInput = row.querySelector('input[name^="exam_"]');
        const finalCell = row.querySelector('.final-live');
        if (!pgInput || !egInput || !finalCell) return;

        const pg  = parseFloat(pgInput.value);
        const eg  = parseFloat(egInput.value);
        if (!isNaN(pg) && !isNaN(eg)) {
            const final = Math.round((pg * 0.4 + eg * 0.6) * 100) / 100;
            finalCell.textContent = final.toFixed(2);
            finalCell.className = 'final-live fw-semibold ';
            if (final >= 8.5)      finalCell.className += 'text-success';
            else if (final >= 7.0) finalCell.className += 'text-primary';
            else if (final >= 5.5) finalCell.className += 'text-warning';
            else                   finalCell.className += 'text-danger';
        }
    }

    document.querySelectorAll('.grade-input').forEach(function (input) {
        input.addEventListener('input', function () {
            const val = parseFloat(this.value);
            if (isNaN(val) || val < 0 || val > 10) {
                this.classList.add('is-invalid');
            } else {
                this.classList.remove('is-invalid');
                const row = this.closest('tr');
                if (row) calcFinalForRow(row);
            }
        });
    });

    document.querySelectorAll('table tbody tr').forEach(function (row) {
        const cells = row.querySelectorAll('td');
        if (row.querySelector('.grade-input') && cells.length >= 5) {
            cells[cells.length - 1].classList.add('final-live');
        }
    });

    document.querySelectorAll('input[type="file"]').forEach(function (fileInput) {
        fileInput.addEventListener('change', function () {
            const file = this.files[0];
            if (file) {
                let info = fileInput.nextElementSibling;
                if (!info || !info.classList.contains('form-text')) {
                    info = document.createElement('div');
                    info.className = 'form-text text-success mt-1';
                    fileInput.after(info);
                }
                const kb = (file.size / 1024).toFixed(1);
                info.textContent = `✔ ${file.name} (${kb} KB)`;
            }
        });
    });

    document.querySelectorAll('[title]').forEach(function (el) {
        new bootstrap.Tooltip(el, { trigger: 'hover' });
    });

    const gradeForm = document.querySelector('form:has(.grade-input)');
    if (gradeForm) {
        let formDirty = false;
        gradeForm.querySelectorAll('.grade-input').forEach(function (inp) {
            inp.addEventListener('change', () => { formDirty = true; });
        });
        gradeForm.addEventListener('submit', () => { formDirty = false; });
        window.addEventListener('beforeunload', function (e) {
            if (formDirty) {
                e.preventDefault();
                e.returnValue = 'Bạn có thay đổi chưa lưu. Bạn có chắc muốn rời khỏi trang?';
            }
        });
    }

});