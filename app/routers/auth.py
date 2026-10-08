from fastapi import APIRouter, Depends, HTTPException
from app.schemas.user import UserCreate, UserRead
from app.models.user import User

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.core.security import hash_password, verify_password
from app.db.deps import DbSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register_user(db: DbSession, user_in: UserCreate):

    user = User(
        full_name=user_in.full_name,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    db.refresh(user)

    return {
        "message": "user created successfully",
        "data": UserRead.model_validate(user),
    }
