# Tài liệu tổng hợp kế hoạch triển khai dự án Hệ thống điểm danh bằng nhận diện khuôn mặt

## 1. Chốt công nghệ (Tech Stack)

Toàn bộ hệ thống được xây dựng theo kiến trúc **microservices**, đóng gói bằng Docker Compose để đảm bảo tính nhất quán giữa môi trường phát triển và môi trường demo. Việc lựa chọn công nghệ dựa trên hai tiêu chí: **độ quen thuộc của team** và **đáp ứng đầy đủ Rubric chấm điểm**.

### 1.1. Tổng quan các thành phần

| **Thành phần** | **Công nghệ lựa chọn** | **Vai trò trong hệ thống** |
| --- | --- | --- |
| Backend | FastAPI + Uvicorn + SQLAlchemy (Python) | Xử lý API tốc độ cao, code gọn nhẹ, dễ bảo trì |
| Database chính | MySQL 8.0 (docker) | Lưu thông tin sinh viên và log điểm danh, quen thuộc với cả team |
| Cache & Message Queue | Redis (docker) | Bộ nhớ đệm cho khuôn mặt và hàng đợi truyền ảnh sang AI Worker |
| Vector Database | Qdrant | Tìm kiếm khuôn mặt theo cơ chế 1:N với tốc độ cao |
| AI Worker | Celery + DeepFace (RetinaFace) | Chạy ngầm để quét mặt, không làm treo Backend |
| Object Storage | MinIO | Lưu trữ ảnh gốc, đáp ứng yêu cầu Rubric về 3 loại lưu trữ |
| Frontend | React + Vite + Template CoreUI | Giao diện quản trị và luồng camera điểm danh |
| Load Balancer / Proxy | Nginx | Điều phối request, bắt buộc theo Rubric |
| Deployment | Docker Compose | Triển khai toàn bộ hệ thống chỉ với một lệnh duy nhất |

### 1.2. Lý do sử dụng đồng thời ba loại lưu trữ
- **MySQL** lưu dữ liệu dạng văn bản và quan hệ (sinh viên, log điểm danh).
- **Qdrant** lưu vector đặc trưng khuôn mặt phục vụ tìm kiếm tương đồng.
- **MinIO** lưu file ảnh gốc dưới dạng object.

## 2. Phân công nhân sự

| **Hạng mục** | **Nhiệm vụ chi tiết** | **Người phụ trách** |
| --- | --- | --- |
| **Backend & Database** | Xây dựng API FastAPI, config MySQL, Redis, Qdrant, MinIO. | *[Tên SV 1]* |
| **AI & Worker** | Tích hợp DeepFace, viết Celery worker xử lý background task (trích xuất & nhận diện). | *[Tên SV 2]* |
| **Frontend UI/UX** | Dựng giao diện React, tích hợp camera, hiển thị kết quả. | *[Tên SV 3]* |
| **DevOps & Integration**| Đóng gói Docker Compose, config Nginx, ghép nối toàn bộ hệ thống. | *[Tên SV 4]* |

## 3. Checklist báo cáo cuối kỳ

Để đảm bảo đáp ứng đầy đủ rubric, hệ thống trước khi demo cần vượt qua các bài test sau:
- [ ] **Môi trường**: Chạy `docker-compose up -d` thành công không lỗi, các containers ở trạng thái `Up` và `Healthy`.
- [ ] **Chức năng Đăng ký (Register)**: Camera chụp ảnh -> Gửi lên API -> Lưu MinIO -> AI Worker lấy đặc trưng lưu Qdrant -> Log MySQL.
- [ ] **Chức năng Điểm danh (Attendance)**: Nhận diện theo luồng (hoặc upload frame) -> Trả kết quả (Trùng khớp / Không trùng khớp) với thời gian trễ lý tưởng < 2-3 giây.
- [ ] **Lưu trữ chuẩn**: Chứng minh được dữ liệu thực sự nằm ở 3 nơi thông qua các UI quản trị (GUI Database Client cho MySQL, Qdrant Dashboard `localhost:6333/dashboard`, MinIO Console `localhost:9001`).
- [ ] **Xử lý bất đồng bộ**: Minh họa được luồng hệ thống Backend không bị block khi quét AI nhờ cơ chế hàng đợi của Celery & Redis.

## 4. Kết quả rà soát Code (Backend & Worker hiện tại)

Hệ thống đã được cập nhật chuẩn xác theo kiến trúc đề ra:
- **Luồng Upload/Đăng ký**: FastAPI nhận frame -> Đẩy thẳng lên MinIO -> Gửi MinIO object key vào Celery -> Worker tải về -> DeepFace trích xuất -> Ghi Qdrant & MySQL.
- **Luồng Điểm danh**: Tương tự, FastAPI không làm tác vụ nặng. Worker xử lý Qdrant search, ghi log vào MySQL và đẩy `status/similarity` vào Redis để FastAPI trả về frontend.
- **Tính năng mở rộng**: 
  - Tối ưu Dockerfile Worker bằng cách pre-build (tải trước) model DeepFace giúp tránh cold-start. 
  - Fix quan hệ nullable trong MySQL cho các logic log điểm danh trạng thái failed.
  - Sử dụng chung cấu hình Pydantic cho cả Backend và Worker.
