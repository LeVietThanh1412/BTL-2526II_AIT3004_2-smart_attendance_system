#!/bin/bash

# Kiểm tra biến môi trường
if [ -z "$MINIO_ROOT_USER" ] || [ -z "$MINIO_ROOT_PASSWORD" ] || [ -z "$MYSQL_ROOT_PASSWORD" ] || [ -z "$MYSQL_DATABASE" ]; then
    echo "Thiếu biến môi trường cần thiết."
    exit 1
fi

BACKUP_BUCKET="backups"
BACKUP_INTERVAL=${BACKUP_INTERVAL:-86400} # Mặc định 24h

echo "[$(date)] Khởi động dịch vụ Backup..."

# Đợi cấu hình MinIO lên
sleep 10
mc alias set myminio http://minio:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD} 2>/dev/null

# Tạo bucket backup nếu chưa có
mc mb myminio/${BACKUP_BUCKET} --ignore-existing 2>/dev/null

echo "[$(date)] Sẵn sàng thực hiện lịch trình backup mỗi ${BACKUP_INTERVAL} giây."

while true; do
  DATE=$(date +%Y-%m-%d_%H-%M-%S)
  echo "----------------------------------------"
  echo "[$(date)] Bắt đầu tiến trình backup..."
  
  # 1. Backup MySQL
  echo "=> Đang Backup MySQL..."
  if mysqldump -h mysql -u root -p"${MYSQL_ROOT_PASSWORD}" ${MYSQL_DATABASE} > /tmp/db_$DATE.sql; then
      mc cp /tmp/db_$DATE.sql myminio/${BACKUP_BUCKET}/mysql/db_$DATE.sql
      rm /tmp/db_$DATE.sql
      echo "=> MySQL Backup thành công!"
  else
      echo "=> Lỗi: Không thể backup MySQL!"
  fi

  # 2. Backup Qdrant
  echo "=> Đang Backup Qdrant..."
  # Tạo snapshot cho Qdrant collection
  curl -s -X POST "http://qdrant:6333/collections/face_embeddings/snapshots" > /tmp/snap_res.json
  SNAP_NAME=$(jq -r '.result.name' /tmp/snap_res.json)
  
  if [ "$SNAP_NAME" != "null" ] && [ -n "$SNAP_NAME" ]; then
     echo "=> Snapshot created: $SNAP_NAME. Tiến hành tải xuống..."
     curl -s -o /tmp/qdrant_$DATE.snapshot "http://qdrant:6333/collections/face_embeddings/snapshots/$SNAP_NAME"
     mc cp /tmp/qdrant_$DATE.snapshot myminio/${BACKUP_BUCKET}/qdrant/qdrant_$DATE.snapshot
     rm /tmp/qdrant_$DATE.snapshot /tmp/snap_res.json
     echo "=> Qdrant Backup thành công!"
  else
     echo "=> Lỗi: Không thể tạo Qdrant snapshot!"
     cat /tmp/snap_res.json
  fi

  # 3. Đồng bộ/Backup tài liệu ảnh bằng mc mirror (Ví dụ sang thư mục nội bộ container nếu có mount ra ngoài)
  # Tuy nhiên vì lưu nội bộ Object Storage, các ảnh và snapshot đã an toàn trong Minio Volume.
  # Bạn có thể uncomment và cấu hình Remote S3 ở đây dể sao lưu đám mây:
  # mc alias set remotes3 https://s3.amazonaws.com ACCESS_KEY SECRET_KEY
  # mc mirror myminio/${MINIO_BUCKET} remotes3/my-remote-bucket

  echo "[$(date)] Vòng lặp backup hoàn tất. Chờ ${BACKUP_INTERVAL} giây..."
  sleep ${BACKUP_INTERVAL}
done