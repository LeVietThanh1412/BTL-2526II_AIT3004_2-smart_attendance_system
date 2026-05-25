# Smart Attendance System (Hệ Thống Điểm Danh Thông Minh)

Hệ thống điểm danh tự động bằng nhận diện khuôn mặt (Face Recognition) áp dụng kiến trúc **Microservices**. Dự án sử dụng mô hình AI tiên tiến (ArcFace, RetinaFace) kết hợp cùng Vector Database để đảm bảo thời gian nhận diện siêu tốc (<20ms).

---

## Tính Năng Nổi Bật

- **Nhận diện siêu tốc**: Tìm kiếm Vector đa chiều thông qua **Qdrant** ($O(\log N)$) thay vì quét CSDL truyền thống.
- **Xử lý bất đồng bộ**: Dùng **Celery + Redis** đẩy các tác vụ AI nặng (DeepFace) xuống Background Worker, giúp API Backend luôn phản hồi ngay lập tức.
- **Kiến trúc Cloud-Native**: Lưu trữ ảnh gốc qua Object Storage (**MinIO**).
- **Thiết kế Microservices**: 7 container độc lập chạy mượt mà thông qua `docker-compose`.
- **Tính năng nâng cao mới**:
  - **Quản lý ca học (Shift Management)**: Sinh viên phải đăng ký lịch học theo các ca trong tuần. Hệ thống tự động đối chiếu lịch học với thời gian điểm danh thực tế.
  - **Thủ tục Check-out**: Sinh viên bắt buộc phải điểm danh khi ra về (Check-out). Hệ thống có logic cảnh báo và đánh dấu lỗi nếu sinh viên check-out sớm hơn 30 phút so với giờ tan học của ca cuối cùng.
  - **Đánh dấu vắng mặt tự động**: Job chạy ngầm tự động vào 23:59 mỗi ngày để quét và đánh dấu vắng không phép cho các sinh viên có lịch học nhưng không đi học hoặc có đến nhưng quên check-out.
  - **Tùy chỉnh trạng thái**: Quản trị viên (Admin) có thể chỉnh sửa trạng thái điểm danh (từ vắng thành có phép, đi muộn, hoặc lý do khác).
  - **Xuất báo cáo Excel (CSV)**: Thêm nút tải nhanh báo cáo điểm danh dạng file CSV mã hoá UTF-8 BOM giúp mở ngay trên Microsoft Excel không bị lỗi font chữ.
  - **Realtime Dashboard**: Trang quản trị nhật ký điểm danh tự động cập nhật log mới mỗi 5 giây (Polling) giúp Admin giám sát trực quan không cần bấm tải lại trang.

---

## Kiến Trúc Hệ Thống (System Architecture)

Dự án được phân tách thành các service độc lập để tối ưu khả năng mở rộng:

1. **Frontend (Vue 3 + Vite + Nginx)**: Giao diện Check-in và Dashboard Admin.
2. **Backend (FastAPI)**: Xử lý logic, Auth, và điều phối AI.
3. **Worker (Celery)**: Trái tim AI, chạy mô hình DeepFace (ArcFace).
4. **Qdrant**: Vector Database, lưu trữ Face Embeddings.
5. **Redis**: Message Broker cho Celery và Caching.
6. **MinIO**: S3-Compatible Storage, lưu trữ ảnh điểm danh.
7. **MySQL 8.0**: CSDL Quan hệ lưu trữ thông tin sinh viên và log điểm danh.

*(Xem thêm các sơ đồ UML chi tiết trong thư mục `uml/`)*

---

## Cấu Trúc Thư Mục (Monorepo)

Dự án áp dụng mô hình Monorepo, quản lý tập trung toàn bộ code frontend, backend và worker. Chi tiết ý nghĩa từng file:

```bash
/BTL-2526II_AIT3004_2-smart_attendance_system
├── backend                  # Thư mục chứa mã nguồn Backend (FastAPI)
│   ├── Dockerfile           # Cấu hình build Docker cho Backend
│   ├── README.md            # Tài liệu hướng dẫn riêng cho Backend
│   ├── requirements.txt     # Các thư viện Python cần cài đặt
│   └── src                  # Mã nguồn chính
│       ├── api
│       │   ├── __init__.py
│       │   └── v1           # Các endpoint API version 1
│       │       ├── attendance.py # API xử lý chụp ảnh và điểm danh
│       │       ├── auth.py       # API đăng nhập Admin qua JWT
│       │       ├── dashboard.py  # API lấy thống kê cho màn hình Dashboard
│       │       ├── __init__.py
│       │       ├── members.py    # API thêm/sửa/xóa sinh viên
│       │       └── schedule.py   # API quản lý ca học (Shift Management)
│       ├── core
│       │   ├── celery_client.py  # Kết nối tới Celery Worker
│       │   ├── config.py         # Load biến môi trường (.env)
│       │   ├── __init__.py
│       │   ├── qdrant_client.py  # Kết nối tới Vector DB (Qdrant)
│       │   ├── scheduler.py      # Job chạy ngầm (Cron) tự động đánh vắng
│       │   └── security.py       # Logic mã hóa Password & Token
│       ├── database
│       │   ├── Base.py           # Khởi tạo kết nối MySQL bằng SQLAlchemy
│       │   └── __init__.py
│       ├── __init__.py
│       ├── main.py               # Entrypoint chạy FastAPI
│       ├── models                # Định nghĩa các Table trong MySQL
│       │   ├── attendance.py
│       │   ├── face_embedding.py
│       │   ├── __init__.py
│       │   ├── schedule.py
│       │   └── user.py
│       ├── reset_db.py           # Script reset/khởi tạo lại Database
│       ├── schemas               # Định nghĩa dữ liệu đầu vào/ra (Pydantic)
│       │   ├── attendance.py
│       │   ├── __init__.py
│       │   ├── schedule.py
│       │   └── user.py
│       ├── services              # Chứa logic nghiệp vụ lõi
│       │   ├── __init__.py
│       │   ├── member_service.py
│       │   ├── redis_query.py    # Logic Cache dữ liệu
│       │   └── storages.py       # Logic Upload ảnh lên MinIO S3
│       └── utils                 # Các hàm tiện ích dùng chung
│           ├── __init__.py
│           └── video_processor.py
├── backup                        # Chứa service backup dữ liệu
│   ├── backup.sh                 # Script chạy cron đồng bộ MySQL/Qdrant
│   └── Dockerfile                # Cấu hình container Backup
├── demo                          # Thư mục chứa ảnh Demo Giao diện
│   ├── dang_ki_diem_danh.png
│   ├── dang_nhap_admin.png
│   └── dashbroad.png
├── docker-compose-network.yml    # Khai báo Network dùng chung cho Docker
├── docker-compose.yml            # File quan trọng khởi tạo toàn bộ 8 services
├── document.md                   # Chứa tài liệu ghi chú
├── frontend                      # Thư mục chứa mã nguồn Frontend (Vue 3)
│   ├── Dockerfile                # Cấu hình build Docker cho Frontend
│   ├── index.html                # Trang web gốc
│   ├── package.json              # Khai báo thư viện JS
│   ├── pnpm-lock.yaml            # Khóa version thư viện
│   ├── public                    # Thư mục public assets
│   │   ├── favicon.ico
│   │   ├── iai-logo.jpg
│   │   └── manifest.json
│   ├── src                       # Mã nguồn Vue JS
│   │   ├── admin                 # Giao diện dành cho Admin
│   │   │   ├── AdminSidebar.vue
│   │   │   ├── Dashbroad.vue
│   │   │   ├── pages
│   │   │   │   ├── AttendanceLogs.vue
│   │   │   │   ├── Dashboard.vue
│   │   │   │   ├── Login.vue
│   │   │   │   ├── ManageMembers.vue
│   │   │   │   ├── RegisterAttendance.vue
│   │   │   │   └── RegisterSchedule.vue
│   │   │   ├── RecentActivity.vue
│   │   │   ├── StatCard.vue
│   │   │   └── TopHeader.vue
│   │   ├── App.vue               # Component gốc Vue
│   │   ├── main.js               # Entrypoint Vue
│   │   ├── router.js             # Phân luồng các trang (Routing)
│   │   ├── shared                # Thành phần dùng chung
│   │   │   ├── api.js            # Cấu hình Axios gọi backend
│   │   │   ├── dateUtils.js
│   │   │   └── styles.css
│   │   └── user                  # Giao diện dành cho Sinh viên
│   │       └── CheckIn.vue
│   └── vite.config.js            # Cấu hình Vite Build Tool
├── IAILogo                       # Logo nhóm/phòng lab
│   └── 545025868_766707732889973_7037884286218005673_n.jpg
├── ke_hoach_trien_khai.md        # Kế hoạch dự án
├── local_backups                 # Thư mục map với container Backup
├── nginx                         # Chứa cấu hình Nginx Gateway
│   ├── Dockerfile
│   └── nginx.conf                # Cấu hình Reverse Proxy
├── README.md                     # File mô tả tổng quát dự án
├── report                        # Thư mục chứa Báo cáo LaTeX
│   ├── out                       # Thư mục chứa file tạm khi build PDF
│   │   └── report
│   │       ├── pdflatex60265.fls
│   │       ├── report.aux
│   │       ├── report.fdb_latexmk
│   │       ├── report.fls
│   │       ├── report.lof
│   │       ├── report.log
│   │       ├── report.lot
│   │       ├── report.out
│   │       ├── report.pdf
│   │       ├── report.synctex.gz
│   │       └── report.toc
│   ├── report.pdf                # Báo cáo file PDF hoàn chỉnh
│   └── report.tex                # Source code báo cáo LaTeX
├── todo.txt                      # Danh sách việc cần làm
├── uml                           # Thư mục chứa sơ đồ kiến trúc
│   ├── activity_diem_danh.png    # Sơ đồ hoạt động Check-in
│   ├── activity_diem_danh.puml
│   ├── component.png             # Sơ đồ Component
│   ├── component.puml
│   ├── csdl.png                  # Sơ đồ ERD Cơ sở dữ liệu
│   ├── csdl.puml
│   ├── deployment.png            # Sơ đồ triển khai Docker
│   ├── deployment.puml
│   ├── sequency.png              # Sơ đồ tuần tự gọi API
│   ├── sequency.puml
│   ├── usecase.png               # Sơ đồ Use Case
│   ├── usecase.puml
│   └── yeu_cau_can_tuan_thu.md
└── worker                        # Thư mục chứa mã nguồn AI Worker
    ├── Dockerfile                # Cấu hình build Docker cho Worker
    ├── requirements.txt          # Thư viện AI (DeepFace, OpenCV...)
    └── src
        ├── celery_app.py         # Khởi tạo Celery
        ├── face_engine.py        # Module xử lý AI (Trích xuất Vector)
        ├── __init__.py
        └── tasks.py              # Các Background Jobs chạy ngầm

29 directories, 108 files
```
---

## Thông Tin Nhóm Phát Triển

| STT | MSSV | Họ và tên | Vai trò chính |
| --- | --- | --- | --- |
| 1 | 24022454 | **Lê Việt Thành** | Trưởng nhóm, DevOps, Thiết kế hệ thống |
| 2 | 24022406 | **Nguyễn Nhật Minh** | Backend Developer (FastAPI, Redis, MySQL) |
| 3 | 24022364 | **Tạ Duy Khánh** | AI/Worker Developer (DeepFace, Celery) |
| 4 | 24022394 | **Nguyễn Đức Mạnh** | Frontend Developer (Vue3, Dashboard) |




---

---

## Hướng Dẫn Cài Đặt & Chạy Dự Án (Step-by-Step)

Dự án được đóng gói 100% bằng Docker để đảm bảo tính nhất quán trên mọi môi trường. Bạn không cần phải cài đặt thủ công Python, Node.js, hay các Database.

### Bước 1: Yêu cầu chuẩn bị (Prerequisites)
1. **Docker Desktop** (trên Windows/Mac) hoặc **Docker Engine & Docker Compose** (trên Linux).
2. Tối thiểu **4GB RAM trống** (để nạp Model AI Facenet512 vào bộ nhớ của Worker).
3. Đảm bảo các cổng (port) sau trên máy của bạn chưa bị phần mềm khác chiếm dụng:
   - `8080` (Nginx/Frontend)
   - `8000` (FastAPI Backend)
   - `3307` (MySQL - *Map từ 3306 bên trong container ra ngoài*)
   - `6333` (Qdrant Vector DB)
   - `6379` (Redis)
   - `9000 / 9001` (MinIO Object Storage)

### Bước 2: Clone dự án và thiết lập môi trường
Mở Terminal / Command Prompt và chạy lệnh sau:
```bash
# 1. Clone source code từ GitHub (nếu bạn chưa clone)
# git clone <đường-dẫn-repo-của-bạn>
# cd BTL-2526II_AIT3004_2-smart_attendance_system

# 2. Khởi tạo file cấu hình môi trường (.env)
cp .env.example .env
```
*Giải thích:* File `.env` chứa toàn bộ cấu hình lõi (Database password, JWT Secret Key, ngưỡng nhận diện AI `FACE_MATCH_THRESHOLD`...). Bạn có thể mở file này lên để tham khảo hoặc thay đổi mật khẩu nếu muốn triển khai lên server thực tế.

### Bước 3: Khởi chạy toàn bộ hệ thống
Chạy lệnh duy nhất sau để Docker tự động tải, cài đặt các thư viện và khởi động 8 containers:
```bash
# Build và chạy ngầm (-d) toàn bộ hệ thống
docker compose up --build -d
```
⏳ *Lưu ý quan trọng:* Trong **lần chạy đầu tiên**, Docker sẽ phải tải các thư viện AI nặng (TensorFlow, OpenCV) và tải trọng số mô hình Facenet512 (~150MB) từ internet về. Việc này có thể mất từ 5-10 phút tùy tốc độ mạng. Ở các lần chạy sau, hệ thống sẽ khởi động thần tốc trong chưa tới 10 giây.

### Bước 4: Kiểm tra trạng thái hệ thống
Bạn gõ lệnh sau để đảm bảo tất cả 8 containers (bao gồm backend, worker, nginx, mysql, qdrant, redis, minio, backup) đều đang ở trạng thái `Up` (Màu xanh / Đang chạy):
```bash
docker compose ps
```

### Bước 5: Truy cập và Sử dụng
Sau khi hệ thống khởi động thành công, hãy mở trình duyệt web và truy cập:

1. **Giao diện Người dùng & Admin (Frontend):** 
   [http://localhost:8080](http://localhost:8080)
   *Tài khoản Admin mặc định:* Xem hoặc sửa thông tin đăng nhập trong file `.env` mục `ADMIN_USERNAME` / `ADMIN_PASSWORD`.

2. **Giao diện API Docs (Backend Swagger UI):** 
   [http://localhost:8000/docs](http://localhost:8000/docs)
   *Nơi dành cho Developer để test thử các API Backend độc lập.*

3. **Kho ảnh thực tế (MinIO Console):** 
   [http://localhost:9001](http://localhost:9001)
   *Tài khoản đăng nhập mặc định:* Lấy từ `MINIO_ROOT_USER` và `MINIO_ROOT_PASSWORD` trong file `.env`. (Đây là nơi chứa toàn bộ ảnh sinh viên upload lên, được quản lý như Google Drive).

### Bước 6: Theo dõi và Khắc phục lỗi (Troubleshooting)
Bởi vì quá trình xử lý AI (trích xuất khuôn mặt) diễn ra âm thầm ở Background Worker, nếu bạn thấy hệ thống báo "Không nhận ra khuôn mặt" trên UI, hãy xem trực tiếp log của Worker để biết lý do:
```bash
# Xem riêng log của luồng AI (DeepFace / Celery) để kiểm tra Quality Assurance
docker compose logs -f worker

# Xem riêng log của Backend API
docker compose logs -f backend

# Xem log của toàn bộ 8 services
docker compose logs -f
```

### Bước 7: Dọn dẹp / Tắt hệ thống
Khi không làm việc nữa, bạn có thể tắt toàn bộ hệ thống để giải phóng RAM và CPU:
```bash
# Tắt hệ thống nhưng giữ lại TOÀN BỘ dữ liệu trong Database và MinIO
docker compose down

# XÓA HỆ THỐNG VÀ XÓA SẠCH DỮ LIỆU ĐÃ TẠO (Cẩn trọng trước khi dùng!)
docker compose down -v
```

---

## Hình Ảnh Thực Tế & Thiết Kế Kiến Trúc

### 1. Giao Diện (Demo)

**Giao diện đăng nhập Admin an toàn:**
![Admin Login](./demo/dang_nhap_admin.png)

**Bảng điều khiển Thống kê Điểm danh (Realtime):**
![Dashboard](./demo/dashbroad.png)

**Giao diện Sinh viên Check-in / Đăng ký Khuôn mặt:**
![Check-in](./demo/dang_ki_diem_danh.png)

### 2. Sơ Đồ Thiết Kế Hệ Thống (UML)

**Sơ đồ triển khai Microservices (Deployment):**
![Deployment](./uml/deployment.png)

**Sơ đồ luồng gọi API và AI Worker (Sequence):**
![Sequence](./uml/sequency.png)

**Sơ đồ luồng Điểm danh 1-1 (Activity):**
![Activity](./uml/activity_diem_danh.png)

**Sơ đồ Cơ sở dữ liệu (ERD):**
![ERD](./uml/csdl.png)
