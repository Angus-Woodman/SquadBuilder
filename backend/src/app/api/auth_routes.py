"""Authentication routes: register, login, me."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.db.models import User, UserRole
from app.db.session import get_sessionmaker

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Request / response schemas ────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    created_at: str


def _user_response(u: User) -> dict[str, Any]:
    return {
        "id": u.id,
        "email": u.email,
        "display_name": u.display_name,
        "role": u.role.value if isinstance(u.role, UserRole) else u.role,
        "created_at": u.created_at.isoformat() if u.created_at else "",
    }


# ── Endpoints ─────────────────────────────────────────────────────────


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest):
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    Session = get_sessionmaker()
    with Session() as db:
        existing = db.scalar(select(User).where(User.email == req.email.lower()))
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        user = User(
            email=req.email.lower(),
            display_name=req.display_name.strip(),
            password_hash=hash_password(req.password),
            role=UserRole.user,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(user.id, user.role)

    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    Session = get_sessionmaker()
    with Session() as db:
        user = db.scalar(select(User).where(User.email == req.email.lower()))
        if user is None or not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_access_token(user.id, user.role)

    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return _user_response(user)
