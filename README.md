# ห้องเรียนของเรา — Classroom Directory

ไดเรกทอรีเพื่อนร่วมห้อง: ดูข้อมูลเพื่อน ค้นหา และแก้ไขข้อมูลของตัวเอง (FastAPI + SQLite + หน้าเว็บในตัว)

## รันด้วย Docker
```bash
docker compose up --build
```
เปิด http://localhost:8000 (ฐานข้อมูลเก็บที่ `./data/` ตั้ง `SECRET_KEY` ใน `.env` ได้ถ้าต้องการ)

## รันเอง
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## ข้อมูลตัวอย่าง (ไม่บังคับ)
```bash
python seed.py   # สร้างเพื่อน 10 คน รหัสผ่าน demo1234 (ผู้ดูแล: demo_admin)
```

## หมายเหตุ
- คนที่สมัครเป็นคนแรกจะได้เป็นผู้ดูแล (admin) อัตโนมัติ
- ฐานข้อมูลใหม่อยู่ที่ `data/classroom.db` โครงสร้างต่างจากไฟล์ `classroom.db` เดิม (ตาราง skills ถูกแทนที่ด้วยข้อมูลโปรไฟล์) จึงไม่ย้ายข้อมูลเก่ามาให้
- รายละเอียด API ดู `API_SPEC.md`
