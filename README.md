# SA25-26_ClassN01_Group14 : Hệ thống Quản lí sinh viên
##
- **Thành Viên:** Nguyễn Hoàng Sơn  
- **Mã sinh viên:** 23010100
##
- **Thành Viên:** Nguyễn Quốc Thái
- **Mã sinh viên:** 23010225 

## Giới thiệu

QLSV là web application quản lý toàn bộ vòng đời học tập của sinh viên: từ hồ sơ, đăng ký tín chỉ, nhập điểm, đến xuất bảng điểm PDF và báo cáo Excel.

Hệ thống được xây dựng theo kiến trúc 3 tầng (Presentation → Business → Persistence) với Flask, đảm bảo phân tách trách nhiệm rõ ràng và dễ mở rộng.

## Tính năng
 - Xác thực & Bảo mật
 - Quản lý Sinh viên (Admin)

CRUD đầy đủ: thêm, sửa, xoá, xem danh sách
Tìm kiếm & lọc theo: tên/MSSV/lớp, giới tính, học lực, khoa
Phân trang
Import hàng loạt từ CSV (có file mẫu tải về)
Tự động tính GPA & xếp loại học lực sau mỗi lần nhập điểm

- Đăng ký Tín chỉ
 Sinh viên xem danh sách môn và đăng ký / huỷ đăng ký
 Kiểm soát sĩ số tối đa theo từng môn học
 Admin mở/khoá/đóng đăng ký theo từng học kỳ
Admin xem toàn bộ danh sách đăng ký + thống kê sĩ số theo môn

- Quản lý Điểm (Admin)

Nhập/cập nhật điểm quá trình (40%) và thi cuối kỳ (60%)
Hỗ trợ đa học kỳ: mỗi bộ điểm gắn với học kỳ cụ thể
Tính điểm tổng kết live ngay khi nhập
Import điểm hàng loạt từ CSV
Lịch sử thay đổi điểm ghi vào AuditLog

Báo cáo & Xuất dữ liệu

Xuất Excel danh sách sinh viên (auto-width cột, lọc theo học kỳ)
Xuất PDF bảng điểm cá nhân (WeasyPrint, có thể in)
Dashboard: biểu đồ tròn học lực, giới tính, Top 5 GPA

Quản trị hệ thống (Admin)

Quản lý Học kỳ: thêm, sửa, xoá, đặt hiện tại, mở/khoá đăng ký TC
Quản lý Khoa/Ngành: thêm, sửa, xoá
Quản lý Môn học: CRUD + sĩ số tối đa
Quản lý Tài khoản: tạo/xoá, reset mật khẩu, hiển thị trạng thái khoá
Nhật ký hệ thống (AuditLog): toàn bộ thao tác có audit trail

 UI/UX

Dark / Light mode (lưu vào localStorage)
Responsive Bootstrap 5
Flash messages trên mọi trang kể cả trang Login
Cảnh báo rời trang khi điểm chưa lưu
