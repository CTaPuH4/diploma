from typing import Annotated

from app.core.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Получаем полную строку пользователя
    result = await db.execute(
        text("SELECT * FROM users WHERE username = :username"),
        {"username": username}
    )

    user_row = result.fetchone()
    if user_row is None:
        raise credentials_exception

    # Преобразуем в dict
    user_dict = dict(user_row._mapping)

    # Создаём объект User из словаря
    user = User(
        id=user_dict["id"],
        username=user_dict["username"],
        full_name=user_dict.get("full_name"),
        hashed_password=user_dict["hashed_password"],
        role=UserRole(user_dict["role"]),   # важно!
        group_id=user_dict.get("group_id")
    )

    return user
