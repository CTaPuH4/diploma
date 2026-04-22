from datetime import timedelta

from app.database import get_db
from app.models.user import User
from app.schemas.auth import Token, UserRegister
from app.utils.security import (create_access_token, get_password_hash,
                                verify_password)
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    # Проверяем существование пользователя
    result = await db.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": user_data.username}
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким username уже существует"
        )

    if user_data.group_id is not None:
        # Проверка существования группы
        result = await db.execute(
            text("SELECT id FROM groups WHERE id = :group_id"),
            {"group_id": user_data.group_id}
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Группа с id={user_data.group_id} не найдена"
            )

    hashed_password = get_password_hash(user_data.password)

    new_user = User(
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=user_data.role,
        group_id=user_data.group_id
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    access_token = create_access_token(
        data={"sub": new_user.username, "role": new_user.role.value},
        expires_delta=timedelta(minutes=60)
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        text("SELECT * FROM users WHERE username = :username"),
        {"username": form_data.username}
    )

    user_row = result.fetchone()

    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный username или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Преобразуем Row в dict для удобства
    user_dict = dict(user_row._mapping)

    if not verify_password(form_data.password, user_dict["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный username или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user_dict["username"], "role": user_dict["role"]},
        expires_delta=timedelta(minutes=60)
    )

    return {"access_token": access_token, "token_type": "bearer"}
