from typing import List

from app.database import get_db
from app.models.group import Group
from app.models.user import User, UserRole
from app.routers.deps import get_current_user
from app.schemas.group import GroupCreate, GroupRead
from app.utils.rbac import PermissionChecker
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("/", response_model=List[GroupRead])
async def get_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Group).order_by(Group.id))
    return result.scalars().all()


@router.post("/", response_model=GroupRead)
@PermissionChecker(UserRole.admin)
async def create_group(
    group_data: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Group).where(Group.slug == group_data.slug))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A group with this slug already exists",
        )

    new_group = Group(slug=group_data.slug, title=group_data.title)
    db.add(new_group)
    await db.commit()
    await db.refresh(new_group)
    return new_group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
@PermissionChecker(UserRole.admin)
async def delete_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = await db.get(Group, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    await db.delete(group)
    await db.commit()
