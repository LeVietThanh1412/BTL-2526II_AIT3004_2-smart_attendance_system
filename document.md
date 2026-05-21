## Kế hoạch cập nhật nhận diện theo mã sinh viên

### Mục tiêu
- Thêm ô nhập mã sinh viên trên frontend để người dùng nhập trước khi gửi ảnh.
- Backend chỉ so sánh vector theo `student_id` (lọc Qdrant), không tìm toàn bộ.
- Nếu không tìm được vector hoặc độ chính xác thấp thì trả kết quả sai; đúng người thì điểm phải cao.
- Đồng bộ luồng frontend-backend-face engine để tránh nhầm lẫn do so sánh tổng quát (đặc biệt khi ảnh tương tự nhau).

### Phạm vi cập nhật
1) Frontend
- Thêm ô nhập `student_id` tại màn hình Check-in.
- Chặn thao tác gửi ảnh nếu chưa có `student_id` hợp lệ.
- Gửi `student_id` kèm ảnh/khung hình lên backend.
- Hiển thị rõ lỗi: thiếu mã, không tồn tại, điểm thấp.

2) Backend API
- Cập nhật request schema cho endpoint điểm danh để bắt buộc `student_id`.
- Trả về thêm thông tin: `match_score`, `threshold`, `matched`, `reason`.
- Nếu `student_id` không tồn tại hoặc không có vector: trả lỗi rõ ràng (ví dụ 404).

3) Backend logic
- Bước 1: kiểm tra `student_id` có tồn tại hay không.
- Bước 2: tạo embedding từ ảnh đầu vào.
- Bước 3: truy vấn Qdrant với filter theo `student_id` để lấy vector của sinh viên đó.
- Bước 4: tính độ tương đồng và so sánh với ngưỡng.
- Nếu điểm thấp hoặc không có vector: trả kết quả sai và lý do.

4) Face engine / worker
- Nhận thêm `student_id` từ backend.
- Chỉ chạy so khớp trên tập vector đã lọc theo `student_id`.
- Cải thiện độ ổn định:
	- Bổ sung kiểm tra chất lượng ảnh (mờ, thiếu sáng).
	- Chuẩn hóa/align khuôn mặt trước khi trích xuất embedding.
	- Đặt ngưỡng nhận diện theo cấu hình để dễ tinh chỉnh.

### Yêu cầu dữ liệu
- Khi đăng ký sinh viên, lưu vector vào Qdrant kèm payload `student_id`.
- Đảm bảo mỗi `student_id` có tập vector đầy đủ; nếu không có thì trả lỗi sớm.

### Luồng nghiệp vụ mới
1) Người dùng nhập `student_id`.
2) Frontend gửi `student_id` + ảnh lên backend.
3) Backend kiểm tra `student_id` và chỉ so khớp với vector của sinh viên đó.
4) Trả kết quả đúng/sai dựa trên `match_score` và `threshold`.

### Tiêu chí hoàn thành
- Frontend bắt buộc nhập `student_id` trước khi gửi ảnh.
- Backend không còn tìm kiếm toàn bộ Qdrant.
- Trả kết quả sai khi điểm thấp hoặc không có vector.
- Đúng người phải có `match_score` cao hơn ngưỡng đã cấu hình.

### Kiểm thử đề xuất
- Trường hợp đúng người, đúng `student_id` → pass.
- Trường hợp sai người, đúng `student_id` → fail.
- Trường hợp đúng người, sai `student_id` → fail.
- Trường hợp thiếu `student_id` → báo lỗi 400.
- Trường hợp `student_id` không có vector → báo lỗi 404.

### Ghi chú cấu hình
- Đặt các ngưỡng trong config (ví dụ `MATCH_THRESHOLD`, `DETECTION_CONF`).
- Log `match_score`, `student_id`, `reason` để dễ debug.
