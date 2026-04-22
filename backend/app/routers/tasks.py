from typing import List

from app.database import get_db
from app.models.task import Task
from app.models.test_case import TestCase
from app.models.user import User, UserRole
from app.routers.deps import get_current_user
from app.schemas.task import TaskCreate, TaskRead
from app.utils.rbac import PermissionChecker
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskRead)
@PermissionChecker(UserRole.teacher)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создать новое задание (только преподаватель/админ)"""

    # Проверка существования группы
    result = await db.execute(
        text("SELECT id FROM groups WHERE id = :group_id"),
        {"group_id": task_data.group_id}
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Группа с id={task_data.group_id} не найдена"
        )

    # Создаём задание
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

    # Создаём тест-кейсы, если они переданы
    if task_data.test_cases:
        for tc in task_data.test_cases:
            test_case = TestCase(
                task_id=new_task.id,
                input=tc.input,
                output=tc.output,
                is_hidden=tc.is_hidden
            )
            db.add(test_case)
        await db.commit()

    return new_task


@router.get("/", response_model=List[TaskRead])
async def get_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить задания в зависимости от роли пользователя"""
    if current_user.role in [UserRole.admin]:
        result = await db.execute(
            text("SELECT * FROM tasks ORDER BY id DESC")
        )
    elif current_user.role in [UserRole.teacher]:
        result = await db.execute(
            text("SELECT * FROM tasks WHERE created_by_id = :user_id "
                 "ORDER BY id DESC"),
            {'user_id': current_user.id}
            )
    else:
        result = await db.execute(
            text("SELECT * FROM tasks WHERE group_id = :group_id ORDER BY id DESC"),
            {'group_id': current_user.group_id}
        )
    tasks = result.mappings().all()
    return tasks
