from typing import List

from app.database import get_db
from app.models.task import Task
from app.models.test_case import TestCase
from app.models.user import User, UserRole
from app.routers.deps import get_current_user
from app.schemas.task import TaskCreate, TaskRead, TaskDetailRead
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


@router.delete('/{task_id}', status_code=status.HTTP_204_NO_CONTENT)
@PermissionChecker(UserRole.admin, UserRole.teacher)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Удалить задание (только преподаватель/админ)"""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задание с id={task_id} не найдено"
        )

    if (
        current_user.id is not task.created_by_id
        and current_user.role is not UserRole.admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не являетесь создателем этого задания"
        )

    await db.delete(task)
    await db.commit()


@router.get("/{task_id}", response_model=TaskDetailRead)
async def get_task_detail(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить детальную информацию о задании + его тест-кейсы"""

    # Получаем задание
    result = await db.execute(
        text("""
            SELECT id, title, text, deadline, group_id, created_by_id
            FROM tasks
            WHERE id = :task_id
        """),
        {"task_id": task_id}
    )
    task_row = result.fetchone()

    if not task_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задание не найдено"
        )

    task_dict = dict(task_row._mapping)

    if not (
        (current_user.role is UserRole.admin)  # Если не админ
        or (
            current_user.role is UserRole.teacher
            and task_dict['created_by_id'] == current_user.id
        )  # И не преподаватель, который создал это задание
        or (current_user.group_id == task_dict["group_id"])  # И не студент из группы
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вам не доступен просмотр этого задания"
        )

    # Получаем тест-кейсы
    tc_result = await db.execute(
        text("""
            SELECT id, input, output, is_hidden
            FROM test_cases
            WHERE task_id = :task_id
        """),
        {"task_id": task_id}
    )
    test_cases = tc_result.mappings().all()

    return {
        **task_dict,
        "test_cases": test_cases,
    }
