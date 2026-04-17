# Bài tập lớn Thực hành phát triển hệ thống Trí Tuệ Nhân Tạo

## Thông tin nhóm

- 24022454 - Lê Việt Thành (Trưởng nhóm)
- 24022406 - Nguyễn Nhật Minh
- 24022364 - Tạ Duy Khánh
- 24022394 - Nguyễn Đức Mạnh

## Cấu trúc thư mục

```
/
│
├── .github/                        # (Điểm cộng) CI/CD Workflow
│   └── workflows/
│       └── docker-publish.yml      # Script tự động test và đẩy Image lên Docker Hub
│
├── nginx/                          # Tầng Load Balancer / API Gateway
│   ├── nginx.conf                  # File cấu hình định tuyến (Routing)
│   └── Dockerfile                  
│
├── frontend/                       # Tầng Giao diện (React/Vue)
│   ├── public/
│   ├── src/
│   │   ├── admin/                  # Component cho trang quản lý của Admin
│   │   ├── user/                   # Component cho trang Camera quét mặt
│   │   └── shared/                 # Các hàm dùng chung (gọi API, format ngày tháng...)
│   ├── package.json
│   └── Dockerfile                  # Đóng gói code FE thành file tĩnh chạy trên Nginx
│
├── backend/                        # Tầng Logic cốt lõi (FastAPI)
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                 # File khởi chạy FastAPI app
│   │   ├── api/                    # Các file định nghĩa Routes (ví dụ: /upload, /checkin)
│   │   ├── core/                   # Cấu hình môi trường, hàm kết nối (MinIO, Postgres, Qdrant)
│   │   ├── models/                 # Định nghĩa bảng Database (SQLAlchemy)
│   │   └── schemas/                # Định nghĩa data chuẩn (Pydantic)
│   ├── requirements.txt            # Thư viện nhẹ (fastapi, uvicorn, sqlalchemy, redis...)
│   └── Dockerfile
│
├── worker/                         # Tầng Xử lý nền AI (Celery + DeepFace)
│   ├── src/
│   │   ├── __init__.py
│   │   ├── celery_app.py           # Khởi tạo Celery Worker kết nối với Redis
│   │   ├── tasks.py                # Định nghĩa các task chạy ngầm (hàm trích xuất Vector)
│   │   └── face_engine.py          # Lớp bọc thư viện DeepFace
│   ├── requirements.txt            # Thư viện nặng (deepface, tensorflow/pytorch, celery...)
│   └── Dockerfile
│
├── docker-compose.yml              # "Trái tim" của hệ thống, điều phối 8 containers
├── .env.example                    # File chứa các biến môi trường mẫu (chỉ dẫn cho giáo viên)
├── .gitignore                      # Chặn push .env thật, thư mục __pycache__, node_modules
└── README.md                       # Tài liệu hướng dẫn chạy (Yêu cầu bắt buộc để lấy điểm)
```

## Phân chia công việc

| STT | MSSV | Họ và tên | Vai trò chính | Công việc phụ trách |
| --- | --- | --- | --- | --- |
| 1 | 24022454 | Lê Việt Thành | Trưởng nhóm, DevOps | Thiết kế kiến trúc tổng thể; dựng docker-compose; cấu hình Nginx gateway; tổ chức nhánh Git, review và merge code; chuẩn hóa tài liệu README. |
| 2 | 24022406 | Nguyễn Nhật Minh | Backend Developer | Xây dựng FastAPI (routes, schemas, models); kết nối Postgres/Redis/MinIO/Qdrant; xử lý logic checkin/checkout và API cho frontend. |
| 3 | 24022364 | Tạ Duy Khánh | AI/Worker Developer | Xây dựng Celery worker; cài đặt pipeline xử lý ảnh khuôn mặt; triển khai task trích xuất vector bằng DeepFace; tối ưu thời gian xử lý nền. |
| 4 | 24022394 | Nguyễn Đức Mạnh | Frontend Developer, QA | Xây dựng giao diện người dùng và admin; tích hợp API từ backend; kiểm thử chức năng end-to-end; hỗ trợ viết test cơ bản và kiểm tra trải nghiệm người dùng. |

## Ghi chú phối hợp

- Mỗi thành viên chịu trách nhiệm chính phần việc được phân công và hỗ trợ chéo khi tích hợp hệ thống.
- Trưởng nhóm tổng hợp tiến độ hàng tuần, xử lý xung đột mã nguồn và đảm bảo tiến độ nộp bài.

