from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserRead, UserUpdate, UserUpdateSelf, UserChangePassword
from app.routers.deps import get_current_user
from app.utils.rbac import PermissionChecker
from app.utils.security import verify_password, get_password_hash

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserRead])
@PermissionChecker(UserRole.admin)
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список всех пользователей (только админ)"""
    result = await db.execute(
        text("SELECT id, username, full_name, role, group_id FROM users ORDER BY id")
    )
    users = result.mappings().all()
    return users


@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Получить информацию о текущем пользователе"""
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_current_user(
    user_data: UserUpdateSelf,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновить информацию о текущем пользователе"""
    if user_data.full_name is not None:
        await db.execute(
            text("UPDATE users SET full_name = :full_name WHERE id = :user_id"),
            {"full_name": user_data.full_name, "user_id": current_user.id}
        )

    if user_data.group_id is not None:
        # Проверяем существование группы
        g_result = await db.execute(
            text("SELECT id FROM groups WHERE id = :group_id"),
            {"group_id": user_data.group_id}
        )
        if not g_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Группа с id={user_data.group_id} не найдена"
            )

        await db.execute(
            text("UPDATE users SET group_id = :group_id WHERE id = :user_id"),
            {"group_id": user_data.group_id, "user_id": current_user.id}
        )

    await db.commit()

    # Возвращаем обновлённые данные
    result = await db.execute(
        text(
            "SELECT id, username, full_name, role, group_id "
            "FROM users WHERE id = :user_id"
        ),
        {"user_id": current_user.id}
    )
    updated = result.mappings().first()

    return updated


@router.post('/change-password', response_model=UserRead)
async def change_password(
    password_data: UserChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Изменить пароль текущего пользователя"""
    # Проверяем старый пароль
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный старый пароль"
        )

    # Обновляем на новый
    new_hashed = get_password_hash(password_data.new_password)
    await db.execute(
        text("UPDATE users SET hashed_password = :hashed WHERE id = :user_id"),
        {"hashed": new_hashed, "user_id": current_user.id}
    )
    await db.commit()

    # Возвращаем обновлённые данные
    result = await db.execute(
        text(
            "SELECT id, username, full_name, role, group_id "
            "FROM users WHERE id = :user_id"
        ),
        {"user_id": current_user.id}
    )
    updated_user = result.mappings().first()
    return updated_user


@router.patch("/{user_id}", response_model=UserRead)
@PermissionChecker(UserRole.admin)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить пользователя (только админ)"""
    result = await db.execute(
        text("SELECT * FROM users WHERE id = :user_id"),
        {"user_id": user_id}
    )
    user_row = result.fetchone()
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с id={user_id} не найден"
        )

    # Обновляем поля
    if user_data.full_name is not None:
        await db.execute(
            text("UPDATE users SET full_name = :full_name WHERE id = :user_id"),
            {"full_name": user_data.full_name, "user_id": user_id}
        )

    if user_data.role is not None:
        await db.execute(
            text("UPDATE users SET role = :role WHERE id = :user_id"),
            {"role": user_data.role.value, "user_id": user_id}
        )

    if user_data.group_id is not None:
        # Проверяем группу
        g_result = await db.execute(
            text("SELECT id FROM groups WHERE id = :group_id"),
            {"group_id": user_data.group_id}
        )
        if not g_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Группа с id={user_data.group_id} не найдена"
            )
        await db.execute(
            text("UPDATE users SET group_id = :group_id WHERE id = :user_id"),
            {"group_id": user_data.group_id, "user_id": user_id}
        )

    await db.commit()

    # Возвращаем обновлённого пользователя
    result = await db.execute(
        text(
            "SELECT id, username, full_name, role, group_id "
            "FROM users WHERE id = :user_id"
        ),
        {"user_id": user_id}
    )
    updated_user = result.mappings().first()
    return updated_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@PermissionChecker(UserRole.admin)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить пользователя (только админ). Запрещено удалять самого себя."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить самого себя"
        )

    result = await db.execute(
        text("SELECT id FROM users WHERE id = :user_id"),
        {"user_id": user_id}
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с id={user_id} не найден"
        )

    await db.execute(
        text("DELETE FROM users WHERE id = :user_id"),
        {"user_id": user_id}
    )
    await db.commit()


@router.get("/{user_id}", response_model=UserRead)
@PermissionChecker(UserRole.admin)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить пользователя по id (только админ)"""
    result = await db.execute(
        text(
            "SELECT id, username, full_name, role, group_id "
            "FROM users WHERE id = :user_id"
        ),
        {"user_id": user_id}
    )
    user_row = result.mappings().first()
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с id={user_id} не найден"
        )
    return user_row
