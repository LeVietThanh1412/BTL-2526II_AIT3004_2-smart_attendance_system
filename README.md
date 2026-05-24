# Smart Attendance System (Hệ Thống Điểm Danh Thông Minh)

Hệ thống điểm danh tự động bằng nhận diện khuôn mặt (Face Recognition) áp dụng kiến trúc **Microservices**. Dự án sử dụng mô hình AI tiên tiến (ArcFace, RetinaFace) kết hợp cùng Vector Database để đảm bảo thời gian nhận diện siêu tốc (<20ms).

---

## Tính Năng Nổi Bật

- **Nhận diện siêu tốc**: Tìm kiếm Vector đa chiều thông qua **Qdrant** ($O(\log N)$) thay vì quét CSDL truyền thống.
- **Xử lý bất đồng bộ**: Dùng **Celery + Redis** đẩy các tác vụ AI nặng (DeepFace) xuống Background Worker, giúp API Backend luôn phản hồi ngay lập tức.
- **Kiến trúc Cloud-Native**: Lưu trữ ảnh gốc qua Object Storage (**MinIO**).
- **Thiết kế Microservices**: 7 container độc lập chạy mượt mà thông qua `docker-compose`.
- **Tính năng nâng cao mới**:
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
.
├── backend
│   ├── Dockerfile             # Cấu hình build image Docker cho Backend
│   ├── README.md              # Hướng dẫn chi tiết cho phần Backend
│   ├── requirements.txt       # Danh sách các thư viện Python cần cài đặt
│   └── src
│       ├── api
│       │   ├── __init__.py    # Khởi tạo module API
│       │   └── v1
│       │       ├── attendance.py # API xử lý điểm danh (chụp ảnh, xác thực)
│       │       ├── auth.py       # API xác thực người dùng (đăng nhập Admin)
│       │       ├── dashboard.py  # API lấy thống kê cho màn hình Dashboard
│       │       ├── __init__.py   # Khởi tạo module v1
│       │       └── members.py    # API quản lý thông tin sinh viên
│       ├── core
│       │   ├── celery_client.py  # Cấu hình kết nối tới Celery Worker
│       │   ├── config.py         # Đọc và load các biến môi trường (.env)
│       │   ├── __init__.py       # Khởi tạo module core
│       │   ├── qdrant_client.py  # Cấu hình kết nối tới Qdrant Vector DB
│       │   └── security.py       # Xử lý mã hóa mật khẩu, tạo token JWT
│       ├── database
│       │   ├── Base.py           # Khởi tạo kết nối MySQL bằng SQLAlchemy
│       │   └── __init__.py       # Khởi tạo module database
│       ├── __init__.py           # Khởi tạo module src
│       ├── main.py               # Điểm bắt đầu (entrypoint) chạy FastAPI
│       ├── models
│       │   ├── attendance.py     # Định nghĩa table `attendances` trong MySQL
│       │   ├── face_embedding.py # Định nghĩa table `face_embeddings` trong MySQL
│       │   ├── __init__.py       # Khởi tạo module models
│       │   └── user.py           # Định nghĩa table `users` trong MySQL
│       ├── schemas
│       │   ├── attendance.py     # Định nghĩa Pydantic schema cho Attendance API
│       │   ├── __init__.py       # Khởi tạo module schemas
│       │   └── user.py           # Định nghĩa Pydantic schema cho User API
│       ├── services
│       │   ├── __init__.py       # Khởi tạo module services
│       │   ├── member_service.py # Logic nghiệp vụ quản lý sinh viên
│       │   ├── redis_query.py    # Logic tương tác caching với Redis
│       │   └── storages.py       # Logic upload và lưu ảnh gốc vào MinIO
│       └── utils
│           ├── __init__.py       # Khởi tạo module utils
│           └── video_processor.py# Các tiện ích xử lý khung hình/video nếu có
├── docker-compose-network.yml    # Cấu hình mạng riêng biệt cho Docker
├── docker-compose.yml            # File chính khởi tạo 7 containers cùng lúc
├── document.md                   # Tài liệu ghi chú hệ thống
├── frontend
│   ├── Dockerfile                # Cấu hình build image Docker cho Frontend
│   ├── index.html                # Trang web gốc chứa thẻ div '#app'
│   ├── package.json              # Khai báo các thư viện Javascript
│   ├── pnpm-lock.yaml            # Khóa phiên bản của các thư viện JS
│   ├── public
│   │   ├── favicon.ico           # Biểu tượng trang web
│   │   └── manifest.json         # Cấu hình PWA
│   ├── src
│   │   ├── admin
│   │   │   ├── AdminSidebar.vue  # Menu bên trái Admin
│   │   │   ├── Dashbroad.vue     # Bố cục chính trang Admin
│   │   │   ├── pages
│   │   │   │   ├── AttendanceLogs.vue # Lịch sử điểm danh chi tiết
│   │   │   │   ├── Dashboard.vue      # Thống kê tổng quan (Admin)
│   │   │   │   └── RegisterAttendance.vue # Đăng ký khuôn mặt sinh viên
│   │   │   ├── RecentActivity.vue# Các hoạt động gần nhất
│   │   │   ├── StatCard.vue      # Card thống kê
│   │   │   └── TopHeader.vue     # Thanh menu trên cùng
│   │   ├── App.vue               # Component gốc VueJS
│   │   ├── main.js               # Điểm bắt đầu (entrypoint) VueJS
│   │   ├── router.js             # Điều hướng (routing) các trang
│   │   ├── shared
│   │   │   ├── api.js            # Khởi tạo axios gọi API
│   │   │   ├── dateUtils.js      # Tiện ích format ngày tháng
│   │   │   └── styles.css        # CSS dùng chung
│   │   └── user
│   │       └── CheckIn.vue       # Giao diện chính để điểm danh
│   └── vite.config.js            # Cấu hình đóng gói Frontend bằng Vite
├── ke_hoach_trien_khai.md        # Lập kế hoạch các sprint phát triển
├── nginx
│   ├── Dockerfile                # File build image Nginx Gateway
│   └── nginx.conf                # Cấu hình Reverse Proxy
├── README.md                     # File mô tả tổng quan dự án
├── report
│   ├── out                       # Chứa các file tạm biên dịch LaTeX
│   └── report.tex                # Mã nguồn gốc báo cáo LaTeX
├── todo.txt                      # Các công việc cần làm
├── uml
│   ├── activity_diem_danh.png    # Render sơ đồ hoạt động
│   ├── activity_diem_danh.puml   # Mã nguồn PlantUML Activity
│   ├── component.png             # Render sơ đồ kiến trúc
│   ├── component.puml            # Mã nguồn PlantUML Component
│   ├── deployment.png            # Render sơ đồ triển khai
│   ├── deployment.puml           # Mã nguồn PlantUML Deployment
│   ├── sequency.png              # Render sơ đồ tuần tự
│   ├── sequency.puml             # Mã nguồn PlantUML Sequence
│   ├── usecase.png               # Render sơ đồ Use Case
│   ├── usecase.puml              # Mã nguồn PlantUML Use Case
│   └── yeu_cau_can_tuan_thu.md   # Yêu cầu kỹ thuật dự án
└── worker
    ├── Dockerfile                # File build image Docker cho Worker
    ├── requirements.txt          # Thư viện Python AI (deepface, tf, opencv)
    └── src
        ├── celery_app.py         # Khởi tạo kết nối Celery và Redis
        ├── face_engine.py        # Logic trích xuất AI khuôn mặt
        ├── __init__.py           # Khởi tạo module src worker
        └── tasks.py              # Các hàm chạy nền bất đồng bộ
```

---

## Hướng Dẫn Cài Đặt & Chạy Dự Án

### 1. Yêu Cầu Hệ Thống
- Đã cài đặt **Docker** và **Docker Compose**.
- Cổng (Port) khả dụng: `8080` (Web), `8000` (API), `3306/3307` (MySQL), `6333` (Qdrant), `6379` (Redis), `9000/9001` (MinIO).

### 2. Khởi Tạo Cấu Hình
Hệ thống sử dụng các thông số bảo mật từ file `.env`. Bạn cần copy file mẫu ra môi trường thực:
```bash
cp .env.example .env
```
*(Lưu ý: Mặc định MySQL trong `.env.example` map ra cổng `3307` để tránh đụng độ với MySQL có sẵn ở máy bạn. Hãy mở file `.env` để kiểm tra lại các thông số `FACE_MATCH_THRESHOLD` hay `DEEPFACE_MODEL_NAME` nếu muốn tinh chỉnh).*

### 3. Build & Khởi Chạy
Dùng một lệnh duy nhất để build và run toàn bộ hệ thống (lần đầu sẽ mất thời gian để tải các thư viện AI):
```bash
# Build các image (Frontend, Backend, Worker, Nginx)
docker compose build

# Khởi chạy toàn bộ hệ thống dưới background (-d)
docker compose up -d
```

### 4. Truy Cập Hệ Thống
Sau khi các container chạy lên (mất khoảng 1-2 phút để Worker khởi động AI model), bạn có thể truy cập:

- **Giao diện Web (Frontend)**: http://localhost:8080
- **API Docs (Swagger)**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 *(Sử dụng `MINIO_ROOT_USER` / `PASSWORD` trong file `.env` để login)*

### 5. Theo Dõi Log Hệ Thống (Gỡ Lỗi)
Mọi xử lý nhận diện AI đều diễn ra ở Worker. Để theo dõi trực tiếp các cờ QA (Quality Assurance) hay lỗi nhận diện:
```bash
docker compose logs -f worker
```
Hoặc xem toàn bộ log của tất cả services:
```bash
docker compose logs -f
```

---

## Thông Tin Nhóm Phát Triển

| STT | MSSV | Họ và tên | Vai trò chính |
| --- | --- | --- | --- |
| 1 | 24022454 | **Lê Việt Thành** | Trưởng nhóm, DevOps, Thiết kế hệ thống |
| 2 | 24022406 | **Nguyễn Nhật Minh** | Backend Developer (FastAPI, Redis, MySQL) |
| 3 | 24022364 | **Tạ Duy Khánh** | AI/Worker Developer (DeepFace, Celery) |
| 4 | 24022394 | **Nguyễn Đức Mạnh** | Frontend Developer (Vue3, Dashboard) |


MinIO Storage: http://localhost:9001

## Cơ chế Backup & Đồng bộ Remote S3

Hệ thống tích hợp sẵn service `backup` chạy ngầm, tự động sao lưu dữ liệu và đồng bộ lên nền tảng Remote S3 (như AWS S3, Cloudflare R2, v.v.) để đảm bảo an toàn tuyệt đối.

### 1. Cấu hình Remote S3
Mở file `.env` và cập nhật các thông số sau để kích hoạt đồng bộ đám mây:
```env
REMOTE_S3_URL=https://s3.amazonaws.com
REMOTE_S3_ACCESS_KEY=your_aws_access_key
REMOTE_S3_SECRET_KEY=your_aws_secret_key
REMOTE_S3_BUCKET=your_backup_bucket
```

### 2. Các dữ liệu được Backup
* **MySQL**: Tự động export ra file `.sql` định kỳ (mặc định 24h).
* **Qdrant**: Tự động tạo và tải về bản snapshot của vector database.
* **Tài liệu & Ảnh gốc**: Đồng bộ toàn bộ kho ảnh nhận diện từ MinIO local lên bucket của Remote S3.

### 3. Cách theo dõi tiến trình
Bạn có thể xem log realtime của quá trình backup bằng lệnh:
```bash
docker compose logs -f backup
```
Dữ liệu tại local có thể xem trực tiếp qua giao diện MinIO Console ở cổng `9001` (vào bucket `backups`).

---
> **Lưu ý QA (Quality Assurance)**: Hệ thống được thiết kế với cơ chế Fallback nghiêm ngặt. Nếu ảnh chụp quá tối, mờ, hoặc không nhận diện được rõ khuôn mặt (Threshold < 0.68), Worker sẽ tự động bắn cờ `WARNING/FAIL` và yêu cầu người dùng thử lại để đảm bảo không xảy ra hiện tượng **nhận diện nhầm người khác (0% False Positive)**.

