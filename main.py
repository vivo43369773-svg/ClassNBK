import secrets
from collections import Counter
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
from auth import (
    create_access_token,
    get_current_user,
    get_optional_user,
    hash_password,
    require_admin,
    verify_password,
)
from database import DATA_DIR, Base, engine, get_db
from schemas import (
    PasswordChange,
    ProfileUpdate,
    RegisterIn,
    RoleChange,
    TokenOut,
    UserOut,
)

Base.metadata.create_all(bind=engine)


def _migrate() -> None:
    """เพิ่มคอลัมน์ใหม่ให้ฐานข้อมูลเดิมที่สร้างไว้ก่อนมีฟีเจอร์รูปโปรไฟล์"""
    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    if "avatar" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar VARCHAR(80)"))


_migrate()

AVATAR_DIR = DATA_DIR / "avatars"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)
MAX_AVATAR_BYTES = 2 * 1024 * 1024

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Classroom Directory API", version="2.0.0")

# ใช้ Bearer token ใน header (ไม่ใช้ cookie) จึงเปิด origin กว้างได้โดยไม่ต้อง allow_credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")

CurrentUser = Annotated[models.User, Depends(get_current_user)]
OptionalUser = Annotated[models.User | None, Depends(get_optional_user)]


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def serialize(user: models.User, viewer: models.User | None) -> UserOut:
    """แปลง User เป็น response โดยซ่อนช่องทางติดต่อตามสิทธิ์ของผู้ดู"""
    out = UserOut.model_validate(
        {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "created_at": user.created_at,
            "full_name": user.full_name,
            "nickname": user.nickname,
            "student_no": user.student_no,
            "favorite_subject": user.favorite_subject,
            "hobbies": user.hobbies or [],
            "bio": user.bio,
            "share_contact": user.share_contact,
            "avatar_url": f"/media/avatars/{user.avatar}" if user.avatar else None,
        }
    )
    if viewer is None:
        out.contact_locked = "login"
    elif user.share_contact or viewer.id == user.id or viewer.role == "admin":
        out.email = user.email
        out.phone = user.phone
        out.line_id = user.line_id
        out.instagram = user.instagram
        out.birthday = user.birthday
    else:
        out.contact_locked = "private"
    return out


def sniff_image_ext(data: bytes) -> str | None:
    """ตรวจชนิดรูปจากเนื้อไฟล์จริง (ไม่เชื่อนามสกุลหรือ content-type ที่ client ส่งมา)"""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def remove_avatar_file(user: models.User) -> None:
    if user.avatar:
        try:
            (AVATAR_DIR / Path(user.avatar).name).unlink(missing_ok=True)
        except OSError:
            pass


def admin_count(db: Session) -> int:
    return db.query(func.count(models.User.id)).filter(models.User.role == "admin").scalar()


def token_response(user: models.User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.id), user=serialize(user, user))


# ---------------------------------------------------------------
# Auth
# ---------------------------------------------------------------

@api.post("/auth/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == body.username).first():
        raise HTTPException(status_code=409, detail="ชื่อผู้ใช้นี้ถูกใช้แล้ว")

    is_first_user = db.query(func.count(models.User.id)).scalar() == 0
    user = models.User(
        username=body.username,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        nickname=body.nickname,
        hobbies=[],
        role="admin" if is_first_user else "member",  # คนแรกเป็นผู้ดูแลห้อง
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="ชื่อผู้ใช้นี้ถูกใช้แล้ว")
    db.refresh(user)
    return token_response(user)


@api.post("/auth/login", response_model=TokenOut)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    user = (
        db.query(models.User)
        .filter(models.User.username == form.username.strip().lower())
        .first()
    )
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token_response(user)


# ---------------------------------------------------------------
# โปรไฟล์ของฉัน
# ---------------------------------------------------------------

@api.get("/me", response_model=UserOut)
def read_me(me: CurrentUser):
    return serialize(me, me)


@api.patch("/me", response_model=UserOut)
def update_me(body: ProfileUpdate, me: CurrentUser, db: Session = Depends(get_db)):
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field == "hobbies":
            value = value or []
        if field == "share_contact" and value is None:
            continue
        setattr(me, field, value)
    db.commit()
    db.refresh(me)
    return serialize(me, me)


@api.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    me: CurrentUser,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    data = await file.read(MAX_AVATAR_BYTES + 1)
    if len(data) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=413, detail="รูปมีขนาดเกิน 2 MB")
    ext = sniff_image_ext(data)
    if not ext:
        raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์ JPG, PNG หรือ WebP")

    name = f"{me.id}-{secrets.token_hex(6)}.{ext}"  # ชื่อสุ่มเพื่อไม่ให้เบราว์เซอร์ใช้รูปเก่าที่แคชไว้
    (AVATAR_DIR / name).write_bytes(data)
    remove_avatar_file(me)
    me.avatar = name
    db.commit()
    db.refresh(me)
    return serialize(me, me)


@api.delete("/me/avatar", response_model=UserOut)
def delete_avatar(me: CurrentUser, db: Session = Depends(get_db)):
    remove_avatar_file(me)
    me.avatar = None
    db.commit()
    db.refresh(me)
    return serialize(me, me)


@api.post("/me/password", status_code=204)
def change_password(body: PasswordChange, me: CurrentUser, db: Session = Depends(get_db)):
    if not verify_password(body.current_password, me.hashed_password):
        raise HTTPException(status_code=400, detail="รหัสผ่านปัจจุบันไม่ถูกต้อง")
    me.hashed_password = hash_password(body.new_password)
    db.commit()


@api.delete("/me", status_code=204)
def delete_me(me: CurrentUser, db: Session = Depends(get_db)):
    if me.role == "admin" and admin_count(db) == 1:
        others = db.query(func.count(models.User.id)).scalar() - 1
        if others > 0:
            raise HTTPException(
                status_code=400,
                detail="คุณเป็นผู้ดูแลคนสุดท้าย กรุณาแต่งตั้งผู้ดูแลคนอื่นก่อนลบบัญชี",
            )
    remove_avatar_file(me)
    db.delete(me)
    db.commit()


# ---------------------------------------------------------------
# ไดเรกทอรี
# ---------------------------------------------------------------

@api.get("/users", response_model=list[UserOut])
def list_users(
    viewer: OptionalUser,
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="ค้นหาจากชื่อ ชื่อเล่น งานอดิเรก วิชาที่ชอบ ฯลฯ"),
    hobby: str | None = Query(None, description="กรองตามงานอดิเรก"),
):
    users = db.query(models.User).order_by(models.User.id).all()

    if hobby:
        h = hobby.strip().lower()
        users = [u for u in users if any(x.lower() == h for x in (u.hobbies or []))]

    if q and q.strip():
        needle = q.strip().lower()

        def haystack(u: models.User) -> str:
            parts = [u.username, u.full_name, u.nickname, u.student_no,
                     u.favorite_subject, u.bio, *(u.hobbies or [])]
            return " ".join(p for p in parts if p).lower()

        users = [u for u in users if needle in haystack(u)]

    return [serialize(u, viewer) for u in users]


@api.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, viewer: OptionalUser, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้")
    return serialize(user, viewer)


# ---------------------------------------------------------------
# ผู้ดูแล
# ---------------------------------------------------------------

@api.patch("/users/{user_id}/role", response_model=UserOut)
def change_role(
    user_id: int,
    body: RoleChange,
    admin: Annotated[models.User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้")
    if user.role == "admin" and body.role == "member" and admin_count(db) == 1:
        raise HTTPException(status_code=400, detail="ต้องมีผู้ดูแลอย่างน้อยหนึ่งคน")
    user.role = body.role
    db.commit()
    db.refresh(user)
    return serialize(user, admin)


@api.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    admin: Annotated[models.User, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="ใช้เมนูลบบัญชีของตัวเองแทน")
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้")
    remove_avatar_file(user)
    db.delete(user)
    db.commit()


# ---------------------------------------------------------------
# สถิติของห้อง (ไม่เปิดเผยข้อมูลส่วนตัว)
# ---------------------------------------------------------------

def _top(counter: Counter, names: dict, limit: int):
    return [
        {"name": names[key], "count": count}
        for key, count in sorted(counter.items(), key=lambda kv: (-kv[1], names[kv[0]]))[:limit]
    ]


@api.get("/analytics")
def analytics(db: Session = Depends(get_db)):
    users = db.query(models.User).all()

    hobby_count, hobby_name = Counter(), {}
    subject_count, subject_name = Counter(), {}
    complete = 0

    for u in users:
        for h in u.hobbies or []:
            hobby_count[h.lower()] += 1
            hobby_name.setdefault(h.lower(), h)
        if u.favorite_subject:
            k = u.favorite_subject.lower()
            subject_count[k] += 1
            subject_name.setdefault(k, u.favorite_subject)
        if u.full_name and u.bio and u.hobbies:
            complete += 1

    return {
        "total_users": len(users),
        "complete_profiles": complete,
        "admins": sum(1 for u in users if u.role == "admin"),
        "top_hobbies": _top(hobby_count, hobby_name, 10),
        "top_subjects": _top(subject_count, subject_name, 8),
    }


@api.get("/health")
def health():
    return {"status": "ok"}


app.include_router(api)


# ---------------------------------------------------------------
# หน้าเว็บ
# ---------------------------------------------------------------

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/media/avatars", StaticFiles(directory=AVATAR_DIR), name="avatars")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")
