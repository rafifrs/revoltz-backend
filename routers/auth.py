from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from auth_utils import create_access_token, hash_password, verify_password
from database import get_db
from models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    password: str
    role: str  # customer | workshop
    workshop_name: Optional[str] = None
    address: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if data.role == "workshop" and not data.workshop_name:
        raise HTTPException(status_code=400, detail="Workshop name is required for workshop accounts")

    user = User(
        email=data.email,
        full_name=data.full_name,
        phone=data.phone,
        hashed_password=hash_password(data.password),
        role=data.role,
        workshop_name=data.workshop_name,
        address=data.address,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Registration successful", "user_id": user.id}


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "workshop_name": user.workshop_name,
        },
    }
