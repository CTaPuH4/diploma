from typing import List

from app.database import get_db
from app.models.group import Group
from app.models.task import Task
from app.models.test_case import TestCase
from app.models.user import User, UserRole
from app.routers.deps import get_current_user
from app.schemas.task import TaskCreate, TaskDetailRead, TaskRead
from app.utils.rbac import PermissionChecker
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

router = APIRouter(prefix="/tasks", tags=["tasks"])


def serialize_task(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "text": task.text,
        "deadline": task.deadline,
        "group_id": task.group_id,
        "created_by_id": task.created_by_id,
        "created_by_full_name": (
            task.created_by.full_name if task.created_by is not None else None
        ),
    }


@router.post("/", response_model=TaskRead)
@PermissionChecker(UserRole.teacher)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if await db.get(Group, task_data.group_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Группа с id={task_data.group_id} не найдена",
        )

    new_task = Task(
        title=task_data.title,
        text=task_data.text,
        deadline=task_data.deadline,
        group_id=task_data.group_id,
        created_by_id=current_user.id,
    )

    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    if task_data.test_cases:
        for tc in task_data.test_cases:
            test_case = TestCase(
                task_id=new_task.id,
                input=tc.input,
                output=tc.output,
                is_hidden=tc.is_hidden,
            )
            db.add(test_case)
        await db.commit()

    return {
        "id": new_task.id,
        "title": new_task.title,
        "text": new_task.text,
        "deadline": new_task.deadline,
        "group_id": new_task.group_id,
        "created_by_id": new_task.created_by_id,
        "created_by_full_name": current_user.full_name,
    }


@router.get("/", response_model=List[TaskRead])
async def get_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Task).options(joinedload(Task.created_by)).order_by(Task.id.desc())

    if current_user.role == UserRole.teacher:
        query = query.where(Task.created_by_id == current_user.id)
    elif current_user.role == UserRole.student:
        query = query.where(Task.group_id == current_user.group_id)

    result = await db.execute(query)
    return [serialize_task(task) for task in result.scalars().all()]


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
@PermissionChecker(UserRole.admin, UserRole.teacher)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задание с id={task_id} не найдено",
        )

    if current_user.id != task.created_by_id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не являетесь автором этого задания",
        )

    await db.delete(task)
    await db.commit()


@router.get("/{task_id}", response_model=TaskDetailRead)
async def get_task_detail(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.test_cases), joinedload(Task.created_by))
        .where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задание не найдено",
        )

    if not (
        current_user.role == UserRole.admin
        or (
            current_user.role == UserRole.teacher
            and task.created_by_id == current_user.id
        )
        or current_user.group_id == task.group_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этому заданию",
        )

    visible_test_cases = (
        [tc for tc in task.test_cases if not tc.is_hidden]
        if current_user.role == UserRole.student
        else task.test_cases
    )

    return {
        **serialize_task(task),
        "test_cases": visible_test_cases,
    }
