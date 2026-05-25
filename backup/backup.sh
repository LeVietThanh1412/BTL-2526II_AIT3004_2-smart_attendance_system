#!/bin/bash

# Thư mục lưu backup cục bộ bên trong container
BACKUP_DIR="/backups"
BACKUP_INTERVAL=${BACKUP_INTERVAL:-86400} # Mặc định 24h

echo "[$(date)] Khởi động dịch vụ Local Backup..."

# Kiểm tra biến môi trường cơ sở
if [ -z "$MYSQL_ROOT_PASSWORD" ] || [ -z "$MYSQL_DATABASE" ]; then
    echo "Lỗi: Thiếu biến môi trường MYSQL_ROOT_PASSWORD hoặc MYSQL_DATABASE."
    exit 1
fi

# Cấu hình MinIO (để tải ảnh gốc về lưu cục bộ luôn nếu sếp muốn)
if [ -n "$MINIO_ROOT_USER" ] && [ -n "$MINIO_ROOT_PASSWORD" ] && [ -n "$MINIO_BUCKET" ]; then
    sleep 10
    mc alias set myminio http://minio:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD} 2>/dev/null
fi

# Tạo các thư mục con để phân loại dữ liệu
mkdir -p ${BACKUP_DIR}/mysql
mkdir -p ${BACKUP_DIR}/qdrant
mkdir -p ${BACKUP_DIR}/minio

echo "[$(date)] Sẵn sàng thực hiện lịch trình backup local mỗi ${BACKUP_INTERVAL} giây."

while true; do
  DATE=$(date +%Y-%m-%d_%H-%M-%S)
  echo "----------------------------------------"
  echo "[$(date)] Bắt đầu tiến trình backup local..."
  
  # 1. Backup MySQL
  echo "=> Đang Backup MySQL..."
  if mysqldump -h mysql -u root -p"${MYSQL_ROOT_PASSWORD}" ${MYSQL_DATABASE} > ${BACKUP_DIR}/mysql/db_$DATE.sql; then
      echo "=> MySQL Backup thành công: ${BACKUP_DIR}/mysql/db_$DATE.sql"
  else
      echo "=> Lỗi: Không thể backup MySQL!"
  fi

  # 2. Backup Qdrant
  echo "=> Đang Backup Qdrant..."
  # Tạo snapshot cho Qdrant collection
  curl -s -X POST "http://qdrant:6333/collections/face_embeddings/snapshots" > /tmp/snap_res.json
  SNAP_NAME=$(jq -r '.result.name' /tmp/snap_res.json)
  
  if [ "$SNAP_NAME" != "null" ] && [ -n "$SNAP_NAME" ]; then
     echo "=> Snapshot created: $SNAP_NAME. Tiến hành lưu local..."
     # Kéo file snapshot về thư mục backup
     curl -s -o ${BACKUP_DIR}/qdrant/qdrant_$DATE.snapshot "http://qdrant:6333/collections/face_embeddings/snapshots/$SNAP_NAME"
     rm /tmp/snap_res.json
     echo "=> Qdrant Backup thành công: ${BACKUP_DIR}/qdrant/qdrant_$DATE.snapshot"
  else
     echo "=> Lỗi: Không thể tạo Qdrant snapshot!"
     cat /tmp/snap_res.json
  fi

  # 3. Backup ảnh từ MinIO xuống ổ cứng (Đồng bộ)
  if [ -n "$MINIO_BUCKET" ]; then
      echo "=> Đang đồng bộ dữ liệu ảnh từ MinIO xuống local..."
      # Lệnh này sẽ copy ảnh từ MinIO về thư mục ổ cứng. Chạy cực nhanh vì ở cùng mạng LAN.
      mc mirror --overwrite myminio/${MINIO_BUCKET} ${BACKUP_DIR}/minio/${MINIO_BUCKET}
      echo "=> Đồng bộ MinIO thành công!"
  fi

  # 4. Tự động dọn dẹp rác (Retention Policy)
  echo "=> Đang dọn dẹp các bản backup cũ hơn 7 ngày để tránh đầy ổ cứng..."
  find ${BACKUP_DIR}/mysql -type f -name "*.sql" -mtime +7 -exec rm {} \;
  find ${BACKUP_DIR}/qdrant -type f -name "*.snapshot" -mtime +7 -exec rm {} \;

  echo "[$(date)] Vòng lặp backup hoàn tất. Chờ ${BACKUP_INTERVAL} giây..."
  sleep ${BACKUP_INTERVAL}
done