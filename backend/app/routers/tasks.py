from typing import List

from app.database import get_db
from app.models.task import Task
from app.models.user import User, UserRole
from app.routers.deps import get_current_teacher
from app.schemas.task import TaskCreate, TaskRead
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskRead)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Создать новое задание (только преподаватель/админ)"""

    result = await db.execute(
        text("SELECT id FROM groups WHERE id = :group_id"),
        {"group_id": task_data.group_id}
    )

    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Группа с id={task_data.group_id} не найдена"
        )

    new_task = Task(
        title=task_data.title,
        text=task_data.text,
        deadline=task_data.deadline,
        group_id=task_data.group_id,
        created_by_id=current_user.id
    )

    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    return new_task


@router.get("/", response_model=List[TaskRead])
async def get_tasks(
    current_user: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Получить все задания (для преподавателя)"""
    if current_user.role is UserRole.admin:
        result = await db.execute(
            text("SELECT * FROM tasks ORDER BY id DESC")
        )
    else:
        result = await db.execute(
            text("SELECT * FROM tasks WHERE created_by_id = :user_id "
                 "ORDER BY id DESC"),
            {'user_id': current_user.id}
            )
    tasks = result.mappings().all()
    return tasks
