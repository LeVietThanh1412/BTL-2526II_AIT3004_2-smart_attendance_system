import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    MYSQL_URL = os.getenv("MYSQL_URL", "mysql+pymysql://root:root@localhost:3306/attendance_db")
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    FACE_SIMILARITY_THRESHOLD = float(os.getenv("FACE_SIMILARITY_THRESHOLD", "0.6"))

settings = Settings()
