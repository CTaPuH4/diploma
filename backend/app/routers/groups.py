from typing import List

from app.database import get_db
from app.schemas.group import GroupCreate, GroupRead
from app.models.group import Group
from app.models.user import User, UserRole
from app.routers.deps import get_current_user
from app.utils.rbac import PermissionChecker
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get('/', response_model=List[GroupRead])
async def get_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(text("SELECT * FROM groups"))
    groups = result.mappings().all()
    return groups


@router.post('/', response_model=GroupRead)
@PermissionChecker(UserRole.admin)
async def create_group(
    group_data: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        text('SELECT * FROM groups WHERE slug = :slug'),
        {'slug': group_data.slug}
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Группа с таким slug уже существует"
        )

    new_group = Group(
        slug=group_data.slug,
        title=group_data.title
    )
    db.add(new_group)
    await db.commit()
    await db.refresh(new_group)
    return new_group


@router.delete('/{group_id}', status_code=status.HTTP_204_NO_CONTENT)
@PermissionChecker(UserRole.admin)
async def delete_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        text('SELECT * FROM groups WHERE id = :group_id'),
        {'group_id': group_id}
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Группа не найдена"
        )

    await db.execute(
        text('DELETE FROM groups WHERE id = :group_id'),
        {'group_id': group_id}
    )
    await db.commit()
