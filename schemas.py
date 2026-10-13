import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

USERNAME_RE = re.compile(r"^[a-z0-9_.-]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+\-\s()]{6,20}$")

_TEXT_FIELDS = (
    "full_name", "nickname", "student_no", "favorite_subject",
    "bio", "email", "phone", "line_id", "instagram",
)


def _blank_to_none(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


class RegisterIn(BaseModel):
    username: str
    password: str = Field(min_length=6, max_length=128)
    full_name: str | None = Field(default=None, max_length=100)
    nickname: str | None = Field(default=None, max_length=40)

    @field_validator("username", mode="before")
    @classmethod
    def _username(cls, v):
        v = str(v or "").strip().lower()
        if not USERNAME_RE.match(v):
            raise ValueError("ชื่อผู้ใช้ต้องยาว 3-30 ตัว ใช้ได้เฉพาะ a-z 0-9 _ . -")
        return v

    @field_validator("full_name", "nickname", mode="before")
    @classmethod
    def _clean(cls, v):
        return _blank_to_none(v)


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=100)
    nickname: str | None = Field(default=None, max_length=40)
    student_no: str | None = Field(default=None, max_length=20)
    favorite_subject: str | None = Field(default=None, max_length=60)
    hobbies: list[str] | None = None
    bio: str | None = Field(default=None, max_length=300)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    line_id: str | None = Field(default=None, max_length=60)
    instagram: str | None = Field(default=None, max_length=60)
    birthday: date | None = None
    share_contact: bool | None = None

    @field_validator(*_TEXT_FIELDS, mode="before")
    @classmethod
    def _clean(cls, v):
        return _blank_to_none(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        if v is not None and not EMAIL_RE.match(v):
            raise ValueError("รูปแบบอีเมลไม่ถูกต้อง")
        return v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        if v is not None and not PHONE_RE.match(v):
            raise ValueError("เบอร์โทรใช้ได้เฉพาะตัวเลข + - ( ) และเว้นวรรค")
        return v

    @field_validator("instagram")
    @classmethod
    def _instagram(cls, v):
        if v is None:
            return v
        v = v.lstrip("@")
        if not re.match(r"^[A-Za-z0-9._]{1,30}$", v):
            raise ValueError("ชื่อ Instagram ใช้ได้เฉพาะ a-z 0-9 . _")
        return v

    @field_validator("hobbies", mode="before")
    @classmethod
    def _hobbies(cls, v):
        if v is None:
            return v
        if not isinstance(v, list):
            raise ValueError("งานอดิเรกต้องเป็นรายการ")
        seen, out = set(), []
        for item in v:
            item = str(item).strip()
            if not item:
                continue
            if len(item) > 30:
                raise ValueError("งานอดิเรกแต่ละอย่างยาวได้ไม่เกิน 30 ตัวอักษร")
            key = item.lower()
            if key not in seen:
                seen.add(key)
                out.append(item)
        if len(out) > 12:
            raise ValueError("เพิ่มงานอดิเรกได้ไม่เกิน 12 อย่าง")
        return out

    @field_validator("birthday")
    @classmethod
    def _birthday(cls, v):
        if v is not None and (v > date.today() or v.year < 1900):
            raise ValueError("วันเกิดไม่ถูกต้อง")
        return v


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


class RoleChange(BaseModel):
    role: Literal["member", "admin"]


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime | None = None

    full_name: str | None = None
    nickname: str | None = None
    student_no: str | None = None
    favorite_subject: str | None = None
    hobbies: list[str] = []
    bio: str | None = None
    share_contact: bool = True
    avatar_url: str | None = None

    # ช่องทางติดต่อ: เป็น null เมื่อผู้ดูไม่มีสิทธิ์เห็น ดูเหตุผลที่ contact_locked
    email: str | None = None
    phone: str | None = None
    line_id: str | None = None
    instagram: str | None = None
    birthday: date | None = None
    contact_locked: Literal["login", "private"] | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
