# Smart Attendance Backend

Backend for student face registration and attendance verification.

## AI Role Separation

- `YOLO`: detects and crops face regions from input frame.
- `Embedding model (ArcFace via InsightFace)`: converts cropped face into numeric embedding vector.
- Attendance verification compares vectors by cosine similarity.

## Processing Flow

### 1) Member Registration

Endpoint: `POST /api/v1/members/register`

- Client sends `student_id`, `name`, and multiple face images (`images_base64`).
- Backend saves raw images for auditing.
- For each image: YOLO detect -> crop -> ArcFace embedding.
- Build `master embedding` using average vector.
- Save user + embedding in MySQL.
- Cache embedding in Redis key `user:{student_id}:embedding`.

### 2) Attendance Verification

Endpoint: `POST /api/v1/attendance/verify`

- Client sends `student_id` + current face frame (`image_base64`).
- Backend loads master embedding from Redis; if miss, load from MySQL and re-cache.
- Current frame: YOLO detect -> crop -> ArcFace embedding.
- Compare cosine similarity.
- Write attendance log into MySQL with status `success` or `failed`.

## Database Schema (MySQL)

- `users`: `id`, `student_id`, `name`, `created_at`, `updated_at`
- `face_embeddings`: `id`, `user_id`, `embedding_vector`, `image_paths`, `updated_at`
- `attendance_logs`: `id`, `user_id`, `similarity_score`, `status`, `captured_image_path`, `timestamp`

## Environment Variables

Set these in your external `.env` file (outside this folder if you prefer):

- `APP_NAME=Smart Attendance API`
- `APP_VERSION=1.0.0`
- `DEBUG=false`
- `MYSQL_URL=mysql+pymysql://root:root@localhost:3306/attendance_db`
- `REDIS_URL=redis://localhost:6379/0`
- `STORAGE_ROOT=storage`
- `STORAGE_BASE_URL=`
- `YOLO_MODEL_PATH=models/yolov8n-face.pt`
- `FACE_SIMILARITY_THRESHOLD=0.6`
- `MIN_REGISTRATION_IMAGES=3`
- `REDIS_EMBEDDING_TTL_SECONDS=86400`

## Run Locally

```bash
pip install -r requirements.txt
uvicorn src.main:app --reload
```

Health check: `GET /health`

## API Payload Examples

### Register

```json
{
	"student_id": "24022454",
	"name": "Nguyen Van A",
	"images_base64": [
		"data:image/jpeg;base64,/9j/4AAQSk...",
		"data:image/jpeg;base64,/9j/4AAQSk...",
		"data:image/jpeg;base64,/9j/4AAQSk..."
	]
}
```

### Verify Attendance

```json
{
	"student_id": "24022454",
	"image_base64": "data:image/jpeg;base64,/9j/4AAQSk..."
}
```
