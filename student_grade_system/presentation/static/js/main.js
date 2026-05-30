// presentation/static/js/main.js

document.addEventListener("DOMContentLoaded", function () {
    console.log("Hệ thống QLSV 3 Tầng - Tải thành công Presentation Static JS!");

    // 1. Tự động ẩn các hộp thông báo Flash Alert của Flask sau 4 giây để không che mắt người dùng
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(function (alert) {
        setTimeout(function () {
            // Sử dụng hiệu ứng mờ dần (Bootstrap Fade)
            alert.classList.add("fade");
            setTimeout(function () {
                alert.remove();
            }, 500);
        }, 4000); 
    });

    // 2. Chức năng Client-side Validation: Kiểm tra dữ liệu Form Thêm Sinh Viên trước khi đẩy lên API Gateway
    const studentForm = document.querySelector("form");
    if (studentForm) {
        studentForm.addEventListener("submit", function (event) {
            const studentCodeInput = document.querySelector("input[name='student_code']");
            const fullNameInput = document.querySelector("input[name='full_name']");

            if (studentCodeInput && fullNameInput) {
                const studentCode = studentCodeInput.value.trim();
                const fullName = fullNameInput.value.trim();

                // Kiểm tra độ dài mã sinh viên
                if (studentCode.length < 3) {
                    alert("Lỗi nhập liệu: Mã sinh viên (MSSV) không được ngắn hơn 3 ký tự!");
                    event.preventDefault(); // Chặn đứng lệnh submit gửi đi
                    return false;
                }

                // Kiểm tra họ tên không được chứa số vô lý
                const hasNumber = /\d/;
                if (hasNumber.test(fullName)) {
                    alert("Lỗi nhập liệu: Họ và tên sinh viên không được phép chứa ký tự số!");
                    event.preventDefault(); // Chặn đứng lệnh submit
                    return false;
                }
            }
        });
    }
});

// 3. Hàm bổ trợ hiển thị hộp thoại xác nhận khi người dùng thao tác các tính năng nguy hiểm (như Đăng xuất)
function confirmLogout(event) {
    if (!confirm("Bạn có chắc chắn muốn đăng xuất và hủy phiên làm việc Token JWT hiện tại không?")) {
        event.preventDefault();
    }
}