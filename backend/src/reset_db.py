import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from sqlalchemy import text
from src.database import engine
from src.database.Base import Base
from src.models.attendance import Attendance
from src.models.schedule import StudentSchedule

with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS attendances"))
    conn.commit()

# create all tables
Base.metadata.create_all(bind=engine)
print("Database reset successful!")
