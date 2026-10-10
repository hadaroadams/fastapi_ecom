from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.schemas.user import UserCreate, UserRead
from app.models.user import User


from app.core.security import hash_password, verify_password, create_access_token
from app.db.deps import DbSession
from app.core.auth import CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register_user(db: DbSession, user_in: UserCreate):

    user = User(
        full_name=user_in.full_name,
        email=user_in.email.lower(),
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


@router.post("/login")
def login_user(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    user = db.scalar(select(User).where(User.email == form.username.lower()))

    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"www-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    return {
        "access_token": create_access_token(user_id=user.id),
        "token_type": "bearer",
    }


@router.get("/me")
def get_user_profile(current_user: CurrentUser):
    return {
        "message": "User details received successfully",
        "data": UserRead.model_validate(current_user),
    }
