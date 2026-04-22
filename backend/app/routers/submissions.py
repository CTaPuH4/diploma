from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List

from app.database import get_db
from app.models.user import User, UserRole
from app.models.submission import Submission, SubmissionStatus
from app.schemas.submission import (
    SubmissionBase,
    StudentSubmissionRead,
    TeacherSubmissionRead,
    SubmissionResponse,
    TeacherSubmissionUpdate
)
from app.utils.rbac import PermissionChecker
from app.routers.deps import get_current_user

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("/", response_model=SubmissionResponse)
@PermissionChecker(UserRole.student)
async def create_submission(
    submission_data: SubmissionBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Студент подаёт решение на задание"""
    result = await db.execute(
        text("""
            SELECT id, group_id FROM tasks WHERE id = :task_id
        """),
        {"task_id": submission_data.task_id}
    )
    task = result.fetchone()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задание не найдено"
        )

    if task.group_id != current_user.group_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете подавать решения только на задания своей группы"
        )

    # Создаём сабмишен
    new_submission = Submission(
        task_id=submission_data.task_id,
        user_id=current_user.id,
        code=submission_data.code,
        language=submission_data.language,
        status=SubmissionStatus.submitted
    )

    db.add(new_submission)
    await db.commit()
    await db.refresh(new_submission)

    # === ЗАГЛУШКИ ===
    # TODO: Запуск автотестов
    # TODO: Отправка кода на анализ LLM
    print(f"[ЗАГЛУШКА] Сабмишен #{new_submission.id} создан.")

    return new_submission


@router.get("/me", response_model=List[StudentSubmissionRead])
@PermissionChecker(UserRole.student)
async def get_my_submissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Студент получает свои все решения"""
    result = await db.execute(
        text("""
            SELECT *
            FROM submissions
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """),
        {"user_id": current_user.id}
    )

    submissions = result.mappings().all()
    return submissions


@router.get("/task/{task_id}", response_model=List[TeacherSubmissionRead])
@PermissionChecker(UserRole.teacher)
async def get_submissions_by_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Преподаватель получает все решения по конкретному заданию"""

    if current_user.role is UserRole.teacher:
        result = await db.execute(
            text("SELECT created_by_id FROM tasks WHERE id = :task_id"),
            {"task_id": task_id}
        )
        task = result.fetchone()
        if not task or task.created_by_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете просматривать решения только по своим заданиям"
            )

    result = await db.execute(
        text("""
            SELECT
                s.id, s.task_id, s.user_id, s.code, s.language,
                s.status, s.test_result, s.llm_comment, s.final_comment,
                s.grade, s.created_at,
                u.full_name as student_full_name
            FROM submissions s
            JOIN users u ON s.user_id = u.id
            WHERE s.task_id = :task_id
            ORDER BY s.created_at DESC
        """),
        {"task_id": task_id}
    )

    submissions = result.mappings().all()
    return submissions


@router.get("/{submission_id}", response_model=TeacherSubmissionRead)
@PermissionChecker(UserRole.teacher)
async def get_submission_by_id(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Преподаватель получает конкретное решение по ID"""
    result = await db.execute(
        text("""
            SELECT
                s.id, s.task_id, s.user_id, s.code, s.language,
                s.status, s.test_result, s.llm_comment, s.final_comment,
                s.grade, s.created_at,
                u.full_name as student_full_name
            FROM submissions s
            JOIN users u ON s.user_id = u.id
            WHERE s.id = :submission_id
        """),
        {"submission_id": submission_id}
    )

    submission = result.mappings().first()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сабмишен не найден"
        )

    # Проверяем, что преподаватель может видеть этот сабмишен
    if current_user.role is UserRole.teacher:
        result = await db.execute(
            text("""
                SELECT t.created_by_id
                FROM tasks t
                JOIN submissions s ON t.id = s.task_id
                WHERE s.id = :submission_id
            """),
            {"submission_id": submission_id}
        )
        task_creator = result.scalar()
        if task_creator != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете просматривать только решения по своим заданиям"
            )

    return submission


@router.patch("/{submission_id}", response_model=StudentSubmissionRead)
@PermissionChecker(UserRole.teacher, UserRole.admin)
async def grade_submission(
    submission_id: int,
    update_data: TeacherSubmissionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Преподаватель выставляет оценку и финальный комментарий"""

    result = await db.execute(
        text("SELECT * FROM submissions WHERE id = :submission_id"),
        {"submission_id": submission_id}
    )
    submission_row = result.fetchone()

    if not submission_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сабмишен не найден"
        )

    await db.execute(
        text("UPDATE submissions SET grade = :grade WHERE id = :submission_id"),
        {"grade": update_data.grade, "submission_id": submission_id}
    )

    await db.execute(
        text("UPDATE submissions SET final_comment = :final_comment "
             "WHERE id = :submission_id"),
        {"final_comment": update_data.final_comment, "submission_id": submission_id}
    )

    if update_data.grade >= 25:
        new_status = SubmissionStatus.passed.value
    else:
        new_status = SubmissionStatus.failed.value
    await db.execute(
        text("UPDATE submissions SET status = :status WHERE id = :submission_id"),
        {"status": new_status, "submission_id": submission_id}
    )

    await db.commit()

    # Возвращаем обновлённый сабмишен
    result = await db.execute(
        text("""
            SELECT
                s.*, u.full_name as student_full_name
            FROM submissions s
            JOIN users u ON s.user_id = u.id
            WHERE s.id = :submission_id
        """),
        {"submission_id": submission_id}
    )

    updated = result.mappings().first()
    return updated
