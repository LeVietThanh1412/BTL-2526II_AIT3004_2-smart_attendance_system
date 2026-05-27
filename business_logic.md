# Nghiệp Vụ & Logic Hệ Thống Điểm Danh Thông Minh

Tài liệu này mô tả chi tiết các luồng nghiệp vụ cốt lõi và logic xử lý bên dưới hệ thống điểm danh, đặc biệt nhấn mạnh thiết kế điểm danh Đa Phiên (Multi-session).

## 1. Quản lý Tài khoản & Đăng ký Dữ liệu

### 1.1. Đăng ký sinh viên mới
- **Thông tin cơ bản**: Mã sinh viên (student_id), Họ và tên.
- **Khuôn mặt**: Hệ thống hỗ trợ 2 chế độ:
  - **Tải ảnh (Images)**: Backend trích xuất đặc trưng (vector 512 chiều) từ từng ảnh thông qua DeepFace (Facenet512).
  - **Quay video (Video)**: Trích xuất các khung hình ngẫu nhiên từ video và xử lý tương tự ảnh.
- **Lịch học (Schedule)**: Ngay khi đăng ký khuôn mặt, sinh viên phải chọn ca học. Dữ liệu lịch học sẽ được đẩy lên hệ thống dưới dạng chờ duyệt.

### 1.2. Xét duyệt (Admin/Giảng viên)
- Sinh viên sau khi đăng ký sẽ ở trạng thái `is_approved = False`.
- Giảng viên có quyền duyệt/từ chối. Khi một yêu cầu đổi lịch được duyệt, các lịch cũ của cùng thứ sẽ bị vô hiệu hóa (`is_active = False`) để đảm bảo **chỉ có 1 bản ghi lịch duy nhất được áp dụng cho mỗi ngày**.

---

## 2. Quản lý Ca học & Lịch học

Hệ thống chia làm 4 ca học tiêu chuẩn mỗi ngày:
- **Ca 1**: 07:00 - 09:40
- **Ca 2**: 09:50 - 12:30
- **Ca 3**: 13:30 - 16:10
- **Ca 4**: 16:20 - 19:00

**Cơ chế lưu trữ:** Mỗi sinh viên chỉ có tối đa 1 bản ghi `StudentSchedule` mang cờ `is_active = True` trên 1 thứ trong tuần. Trường `shifts` lưu trữ dạng chuỗi (VD: `"1,2,4"`).

---

## 3. Luồng Điểm Danh (Check-in / Check-out Đa Phiên)

Hệ thống hỗ trợ điểm danh **Multi-session**, cho phép sinh viên In-Out nhiều lần trong ngày nếu học các ca rời nhau (Ví dụ học Ca 1, trưa về, chiều lên học Ca 4).

### 3.1. Xác thực Sinh viên & AI Matching
1. Kiểm tra tài khoản (`is_approved == True`), tìm lịch học (`is_active == True`).
2. Gửi ảnh Base64 cho Celery worker chạy hàm `recognize_face_task()` so khớp Qdrant.
3. Chặn không cho điểm danh trước giờ mở cửa (5h30 sáng).

### 3.2. State Machine: Nhận diện Hành Động In / Out
Hệ thống lấy bản ghi điểm danh mới nhất trong ngày (`last_attendance`) để rẽ nhánh:

- **Khởi tạo Check-in (`action = 'check_in'`)**:
  - Xảy ra khi: Chưa có bản ghi nào, HOẶC bản ghi cuối cùng đã đóng (có `check_out_time`), HOẶC bản ghi cuối bị lỗi (`failed`/`absent`).
  - Hành động: Mở một phiên điểm danh mới, lưu `check_in_time`.

- **Thực hiện Check-out (`action = 'check_out'`)**:
  - Xảy ra khi: Bản ghi cuối cùng đang có `status == success` nhưng chưa có `check_out_time`.
  - Thuật toán xác định ca mục tiêu:
    1. Đọc lại `check_in_time` của phiên hiện tại.
    2. Áp vào các ca học sinh viên đã đăng ký để nội suy ra phiên học này thuộc Ca nào (ví dụ Check-in lúc 07:00 thì đây là Ca 1).
    3. Lấy giờ tan học của Ca đó làm mốc. Tính ra Khung giờ Check-out (30 phút cuối ca).
  - Ràng buộc: Nếu chưa tới khung giờ check-out của ca đó $\rightarrow$ báo lỗi. Nếu hợp lệ $\rightarrow$ lưu `check_out_time`.

### 3.3. Thuật toán Dynamic Late Calculation (Tính Giờ Muộn)
Khi Check-in mới, hệ thống cũng nội suy ca học mục tiêu (tương tự như lúc check-out) nhưng dựa vào `current_time`.
- `Late Threshold = (Target Shift Start Time) + 15 phút`.
- Nếu `current_time > Late Threshold` $\rightarrow$ gán cờ `is_late = True`. Cờ này sẽ khóa cứng vào DB (`is_late_override`) để Dashboard gọi ra mà không cần tính lại.

---

## 4. Xử lý Ngoại lệ & Sửa đổi (Admin Override)

### 4.1. Hệ thống tự động (Cronjob `scheduler.py`)
Lúc **23:59**, hệ thống chạy vòng lặp qua tất cả sinh viên có lịch học:
1. **Quét vắng mặt từng ca (Per-shift Absence)**:
   - Đọc danh sách ca học đăng ký (VD: Ca 1, Ca 4).
   - Với mỗi ca, kiểm tra xem có phiên điểm danh (in/out) nào **giao cắt (overlap)** với khung giờ của ca đó không.
   - Nếu sinh viên chỉ In-Out ở Ca 1, thì khi vòng lặp chạy đến Ca 4 sẽ không tìm thấy overlap $\rightarrow$ Hệ thống tự động tạo 1 bản log `Vắng Ca 4`.
2. **Quên check-out**:
   - Quét các phiên điểm danh đang mở (thiếu `check_out_time`). Đổi thành `present_incomplete`.

### 4.2. Giảng viên sửa thủ công (Override)
- **Đi đúng / Vào muộn**: Ghi đè `is_late_override`.
- **Vắng mặt**: Gán trạng thái `absent`. Hệ thống tự xóa `check_in_time` & `check_out_time`.
- **Quên check-out**: Đổi thành `present_incomplete` và tự động set `check_out_time = Null`.

---

## 5. Thống kê & Báo cáo (Dashboard)
- Tính toán số liệu thống kê (Số người đi học, đi muộn) bằng cách dùng hàm `distinct(user_id)`. Do đó, dù sinh viên có 2 dòng log điểm danh (In-Out 2 lần), báo cáo vẫn đếm là 1 người.
- Nhật ký và tính năng Xuất CSV sẽ lấy và hiển thị toàn bộ các phiên điểm danh, phản ánh đúng thực tế tần suất quét khuôn mặt.
