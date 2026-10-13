"""สร้างข้อมูลตัวอย่างสำหรับทดลองใช้ (รันเฉพาะตอนพัฒนา): python seed.py

ทุกบัญชีใช้รหัสผ่าน demo1234 — อย่าใช้กับระบบจริง
"""
from datetime import date

import models
from auth import hash_password
from database import Base, SessionLocal, engine

Base.metadata.create_all(bind=engine)

DEMO = [
    ("demo_admin", "ครูสมศรี ใจดี", "ครูศรี", "1", "ภาษาไทย", ["อ่านหนังสือ", "ทำสวน"], "ครูประจำชั้นค่ะ ยินดีต้อนรับทุกคน", "admin"),
    ("beam", "ภูมิพัฒน์ แสงทอง", "บีม", "2", "คณิตศาสตร์", ["เล่นเกม", "ฟุตบอล", "เขียนโปรแกรม"], "ชอบแก้โจทย์ยากๆ และเล่นบอลตอนเย็น", "member"),
    ("fern", "เฟิร์น วัฒนากุล", "เฟิร์น", "3", "ศิลปะ", ["วาดรูป", "ถ่ายภาพ", "ฟังเพลง"], "วาดรูปทุกวัน รับวาดการ์ตูนให้เพื่อนฟรี", "member"),
    ("nine", "ณัฐวุฒิ ทองดี", "ไนน์", "4", "วิทยาศาสตร์", ["เขียนโปรแกรม", "เล่นเกม"], "อยากเป็นวิศวกรซอฟต์แวร์", "member"),
    ("mint", "มินตรา ศรีสุข", "มิ้นท์", "5", "ภาษาอังกฤษ", ["ดูซีรีส์", "ฟังเพลง", "เต้น"], "ติดซีรีส์เกาหลีและกำลังฝึกภาษาเกาหลี", "member"),
    ("oat", "อธิป พงษ์เจริญ", "โอ๊ต", "6", "พลศึกษา", ["ฟุตบอล", "ว่ายน้ำ"], "กัปตันทีมฟุตบอลห้อง", "member"),
    ("pam", "ปามีลา จันทร์เพ็ญ", "แพม", "7", "ศิลปะ", ["ถ่ายภาพ", "ทำอาหาร"], "ชอบถ่ายรูปเพื่อนๆ ในห้องเก็บไว้", "member"),
    ("ploy", "พลอยชมพู รัตนวงศ์", "พลอย", "8", "ภาษาอังกฤษ", ["อ่านหนังสือ", "เขียนบล็อก"], "", "member"),
    ("top", "ธนกร เกษมสุข", "ท็อป", "9", "คณิตศาสตร์", ["เล่นเกม", "เล่นกีตาร์"], "เล่นกีตาร์ได้สามคอร์ด", "member"),
    ("jane", "เจนจิรา บุญมา", "เจน", "10", "สังคมศึกษา", ["ทำอาหาร", "ดูซีรีส์"], "ถ้าหิวมาหาได้ เดี๋ยวทำขนมให้", "member"),
]

db = SessionLocal()
added = 0
for i, (username, full, nick, no, subj, hobbies, bio, role) in enumerate(DEMO):
    if db.query(models.User).filter_by(username=username).first():
        continue
    db.add(models.User(
        username=username,
        hashed_password=hash_password("demo1234"),
        role=role,
        full_name=full,
        nickname=nick,
        student_no=no,
        favorite_subject=subj,
        hobbies=hobbies,
        bio=bio or None,
        email=f"{username}@example.com",
        line_id=username,
        birthday=date(2009, (i % 12) + 1, (i * 3) % 27 + 1),
        share_contact=(username != "ploy"),  # ตัวอย่างคนที่ไม่แชร์ช่องทางติดต่อ
    ))
    added += 1
db.commit()
print(f"เพิ่มผู้ใช้ตัวอย่าง {added} คน (รหัสผ่าน demo1234)")
