from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Địa chỉ kết nối tới Database (Postgres trong Docker)
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@db:5432/attendance_db"

# 2. Engine: Động cơ chính để thực thi các lệnh SQL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()