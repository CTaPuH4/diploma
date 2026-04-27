from typing import List

from app.database import get_db
from app.models.group import Group
from app.models.user import User, UserRole
from app.routers.deps import get_current_user
from app.schemas.user import UserChangePassword, UserRead, UserUpdate, UserUpdateSelf
from app.utils.rbac import PermissionChecker
from app.utils.security import get_password_hash, verify_password
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/users", tags=["users"])


async def get_user_or_404(db: AsyncSession, user_id: int) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={user_id} was not found",
        )
    return user


@router.get("/", response_model=List[UserRead])
@PermissionChecker(UserRole.admin)
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(User).order_by(User.id))
    return result.scalars().all()


@router.get("/me", response_model=UserRead)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_current_user(
    user_data: UserUpdateSelf,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_or_404(db, current_user.id)

    if user_data.full_name is not None:
        user.full_name = user_data.full_name

    if user_data.group_id is not None:
        if await db.get(Group, user_data.group_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group with id={user_data.group_id} was not found",
            )
        user.group_id = user_data.group_id

    await db.commit()
    return user


@router.post("/change-password", response_model=UserRead)
async def change_password(
    password_data: UserChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_or_404(db, current_user.id)

    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password",
        )

    user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    return user


@router.patch("/{user_id}", response_model=UserRead)
@PermissionChecker(UserRole.admin)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await get_user_or_404(db, user_id)

    if user_data.full_name is not None:
        user.full_name = user_data.full_name

    if user_data.role is not None:
        user.role = user_data.role

    if user_data.group_id is not None:
        if await db.get(Group, user_data.group_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group with id={user_data.group_id} was not found",
            )
        user.group_id = user_data.group_id

    await db.commit()
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@PermissionChecker(UserRole.admin)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )

    user = await get_user_or_404(db, user_id)
    await db.delete(user)
    await db.commit()


@router.get("/{user_id}", response_model=UserRead)
@PermissionChecker(UserRole.admin)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_user_or_404(db, user_id)
