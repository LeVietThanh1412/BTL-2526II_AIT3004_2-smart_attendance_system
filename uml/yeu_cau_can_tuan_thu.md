## Yêu cầu chức năng
- Đăng ký khuôn mặt theo MSSV bằng ảnh (base64) hoặc video.
- Tự động trích xuất embedding từ nhiều ảnh, tính master embedding và lưu vào Qdrant.
- Lưu thông tin sinh viên và log đăng ký vào MySQL.
- Lưu ảnh gốc đăng ký/điểm danh vào MinIO để audit.
- Điểm danh: nhận ảnh từ camera, nhận diện theo MSSV, trả kết quả matched/không matched.
- Cache embedding trên Redis để tăng tốc (sau đăng ký hoặc cache lại khi cần).
- Quản lý sinh viên: thêm/sửa/xóa/tra cứu thông tin.
- Xem lịch sử điểm danh và báo cáo tổng hợp.
- Xuất dữ liệu điểm danh ra CSV/Excel.

## Yêu cầu phi chức năng
- Hiệu năng: phản hồi điểm danh trong vài giây, xử lý song song qua worker.
- Độ tin cậy: retry task, xử lý lỗi worker và thông báo rõ ràng cho người dùng.
- Bảo mật: sử dụng HTTPS, token xác thực, phân quyền theo vai trò.
- Tính sẵn sàng: các service tự khởi động lại khi lỗi (restart policy).
- Mở rộng: cho phép scale backend/worker khi tải tăng.
- Bảo trì: code tách lớp, có log và healthcheck.
- Tính tương thích: hỗ trợ trình duyệt hiện đại và thiết bị di động.
- Sao lưu: có kế hoạch backup MySQL và MinIO định kỳ.
