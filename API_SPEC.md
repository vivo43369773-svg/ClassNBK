# Classroom Directory API (v2)

Base URL: `http://localhost:8000/api` · เอกสารแบบโต้ตอบ: `http://localhost:8000/docs` · หน้าเว็บ: `http://localhost:8000/`

การยืนยันตัวตนใช้ `Authorization: Bearer <access_token>` (token อายุ 12 ชั่วโมง ปรับได้ด้วย `ACCESS_TOKEN_EXPIRE_MINUTES`)

## ข้อมูลผู้ใช้ (User)

| ฟิลด์ | ความหมาย | ใครเห็น |
|---|---|---|
| `id`, `username`, `role` (`member`/`admin`), `created_at` | บัญชี | ทุกคน |
| `full_name`, `nickname`, `student_no`, `favorite_subject`, `hobbies[]`, `bio` | ข้อมูลทั่วไป | ทุกคน |
| `email`, `phone`, `line_id`, `instagram`, `birthday` | ช่องทางติดต่อ | ผู้ที่ล็อกอิน และเจ้าของตั้ง `share_contact = true` (เจ้าของและผู้ดูแลเห็นเสมอ) |
| `share_contact` | เปิด/ปิดการแชร์ช่องทางติดต่อ | ทุกคน |
| `avatar_url` | รูปโปรไฟล์ (ไม่บังคับ) เช่น `/media/avatars/3-ab12cd.jpg` เป็น `null` ถ้าไม่มีรูป | ทุกคน |
| `contact_locked` | `null` / `"login"` (ยังไม่ล็อกอิน) / `"private"` (เจ้าของปิดการแชร์) | ทุกคน |

ขีดจำกัด: `bio` ≤ 300 ตัวอักษร, `hobbies` ≤ 12 อย่าง (อย่างละ ≤ 30 ตัวอักษร), `username` 3-30 ตัว (`a-z 0-9 _ . -`, เก็บเป็นตัวพิมพ์เล็ก), รหัสผ่านอย่างน้อย 6 ตัว

## Auth

### `POST /auth/register` → 201
```json
{ "username": "beam", "password": "secret123", "full_name": "ภูมิพัฒน์ แสงทอง", "nickname": "บีม" }
```
ตอบกลับ `{ "access_token": "...", "token_type": "bearer", "user": { ... } }` · ผู้ใช้คนแรกของระบบจะได้เป็น `admin` ส่วนคนอื่นเป็น `member` เสมอ (ส่ง role มาเองไม่ได้) · ชื่อซ้ำ → 409

### `POST /auth/login`
ส่งแบบ `application/x-www-form-urlencoded` (`username`, `password`) ตอบกลับรูปแบบเดียวกับ register · ผิด → 401

## โปรไฟล์ของฉัน (ต้องล็อกอิน)

| Method | Path | รายละเอียด |
|---|---|---|
| GET | `/me` | ข้อมูลของตัวเอง (เห็นช่องทางติดต่อครบ) |
| PATCH | `/me` | แก้ไขบางฟิลด์ ส่งเฉพาะที่ต้องการเปลี่ยน ส่ง `null` เพื่อล้างค่า |
| POST | `/me/password` | `{ "current_password": "...", "new_password": "..." }` → 204 |
| POST | `/me/avatar` | อัปโหลดรูปโปรไฟล์ (`multipart/form-data` ฟิลด์ `file`) รองรับ JPG/PNG/WebP ไม่เกิน 2 MB ตรวจชนิดจากเนื้อไฟล์ ส่งซ้ำเพื่อเปลี่ยนรูป |
| DELETE | `/me/avatar` | ลบรูปโปรไฟล์ |
| DELETE | `/me` | ลบบัญชีตัวเอง → 204 (ผู้ดูแลคนสุดท้ายลบไม่ได้ถ้ายังมีสมาชิกอื่น) |

ตัวอย่าง `PATCH /me`
```json
{
  "nickname": "บีม",
  "favorite_subject": "คณิตศาสตร์",
  "hobbies": ["เล่นเกม", "ฟุตบอล"],
  "line_id": "beam.s",
  "birthday": "2009-03-14",
  "share_contact": true
}
```

## ไดเรกทอรี (ไม่ต้องล็อกอิน)

| Method | Path | รายละเอียด |
|---|---|---|
| GET | `/users?q=&hobby=` | รายชื่อทั้งหมด `q` ค้นจากชื่อ ชื่อเล่น เลขที่ วิชา แนะนำตัว งานอดิเรก · `hobby` กรองตรงตัว |
| GET | `/users/{id}` | ข้อมูลผู้ใช้รายคน · 404 ถ้าไม่พบ |
| GET | `/analytics` | สถิติของห้อง |
| GET | `/health` | ตรวจสอบสถานะ |

`GET /analytics`
```json
{
  "total_users": 10,
  "complete_profiles": 8,
  "admins": 1,
  "top_hobbies": [{ "name": "เล่นเกม", "count": 3 }],
  "top_subjects": [{ "name": "คณิตศาสตร์", "count": 2 }]
}
```

## ผู้ดูแล (`role = admin`)

| Method | Path | รายละเอียด |
|---|---|---|
| PATCH | `/users/{id}/role` | `{ "role": "admin" | "member" }` (ลดสิทธิ์ผู้ดูแลคนสุดท้ายไม่ได้) |
| DELETE | `/users/{id}` | ลบผู้ใช้อื่น → 204 |

## รหัสข้อผิดพลาด
`400` ข้อมูลไม่ถูกต้องตามเงื่อนไข · `401` ยังไม่ล็อกอินหรือ token หมดอายุ · `403` ไม่มีสิทธิ์ · `404` ไม่พบ · `409` ชื่อผู้ใช้ซ้ำ · `422` รูปแบบข้อมูลไม่ผ่านการตรวจสอบ (รายละเอียดอยู่ใน `detail`)
