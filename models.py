from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, Date, DateTime, Integer, String

from database import Base


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # บัญชี
    username = Column(String(30), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String(10), default="member", nullable=False)  # member | admin
    created_at = Column(DateTime(timezone=True), default=_now)

    # ข้อมูลทั่วไป (ทุกคนเห็น)
    full_name = Column(String(100), nullable=True)
    nickname = Column(String(40), nullable=True)
    student_no = Column(String(20), nullable=True)
    favorite_subject = Column(String(60), nullable=True)
    hobbies = Column(JSON, default=list, nullable=False)
    bio = Column(String(300), nullable=True)

    # ช่องทางติดต่อ (เฉพาะผู้ที่ล็อกอิน และเจ้าของยอมแชร์)
    email = Column(String(120), nullable=True)
    phone = Column(String(30), nullable=True)
    line_id = Column(String(60), nullable=True)
    instagram = Column(String(60), nullable=True)
    birthday = Column(Date, nullable=True)
    share_contact = Column(Boolean, default=True, nullable=False)

    # รูปโปรไฟล์ (ไม่บังคับ) เก็บชื่อไฟล์ใน data/avatars/
    avatar = Column(String(80), nullable=True)
