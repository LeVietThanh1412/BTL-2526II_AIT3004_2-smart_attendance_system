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

  # 3. Đồng bộ dữ liệu và tài liệu ảnh sang Remote S3 (nếu có cấu hình)
  if [ -n "$REMOTE_S3_URL" ] && [ -n "$REMOTE_S3_ACCESS_KEY" ] && [ -n "$REMOTE_S3_SECRET_KEY" ] && [ -n "$REMOTE_S3_BUCKET" ]; then
      echo "=> Đang đồng bộ backup sang Remote S3..."
      mc alias set remotes3 "$REMOTE_S3_URL" "$REMOTE_S3_ACCESS_KEY" "$REMOTE_S3_SECRET_KEY" 2>/dev/null
      
      # Mirror thư mục backup (MySQL & Qdrant)
      mc mirror --overwrite myminio/${BACKUP_BUCKET} remotes3/${REMOTE_S3_BUCKET}/backups
      
      # Mirror bucket tài liệu/ảnh
      if [ -n "$MINIO_BUCKET" ]; then
          mc mirror --overwrite myminio/${MINIO_BUCKET} remotes3/${REMOTE_S3_BUCKET}/${MINIO_BUCKET}_docs
      fi
      echo "=> Đồng bộ Remote S3 thành công!"
  fi

  echo "[$(date)] Vòng lặp backup hoàn tất. Chờ ${BACKUP_INTERVAL} giây..."
  sleep ${BACKUP_INTERVAL}
done