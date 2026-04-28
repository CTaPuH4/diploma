import asyncio
from typing import List

from app.database import get_db
from app.models.submission import Submission, SubmissionStatus
from app.models.submission import SubmissionLanguage
from app.models.task import Task
from app.models.user import User, UserRole
from app.routers.deps import get_current_user
from app.schemas.submission import (
    StudentSubmissionRead,
    SubmissionBase,
    SubmissionResponse,
    TeacherSubmissionRead,
    TeacherSubmissionUpdate,
)
from app.services.judge import format_test_result, judge_submission
from app.services.llm import analyze_submission
from app.services.submission_workflow import has_test_cases, should_run_judge
from app.utils.rbac import PermissionChecker
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

router = APIRouter(prefix="/submissions", tags=["submissions"])


def serialize_teacher_submission(submission: Submission) -> dict:
    return {
        "id": submission.id,
        "task_id": submission.task_id,
        "user_id": submission.user_id,
        "code": submission.code,
        "language": submission.language,
        "status": submission.status,
        "test_result": submission.test_result,
        "llm_comment": submission.llm_comment,
        "final_comment": submission.final_comment,
        "grade": submission.grade,
        "created_at": submission.created_at,
        "student_full_name": submission.user.full_name,
        "inline_comments": submission.inline_comments,
    }


@router.post("/", response_model=SubmissionResponse)
@PermissionChecker(UserRole.student)
async def create_submission(
    submission_data: SubmissionBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, submission_data.task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задание не найдено",
        )

    if task.group_id != current_user.group_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете отправлять решения только для заданий своей группы",
        )

    task_has_test_cases = await has_test_cases(db, task.id)

    new_submission = Submission(
        task_id=submission_data.task_id,
        user_id=current_user.id,
        code=submission_data.code,
        language=submission_data.language,
        status=SubmissionStatus.analyzing,
    )

    db.add(new_submission)
    await db.commit()
    await db.refresh(new_submission)

    should_launch_judge = should_run_judge(
        submission_data.language,
        task_has_test_cases,
    )

    asyncio.create_task(
        analyze_submission(new_submission.id)
    )

    if should_launch_judge:
        asyncio.create_task(
            judge_submission(
                new_submission.id,
                new_submission.code,
                new_submission.task_id,
                new_submission.language,
            )
        )
    else:
        skipped_reasons = []
        if submission_data.language == SubmissionLanguage.other:
            skipped_reasons.append(
                "выбранный язык не поддерживается автоматической проверкой"
            )
        if not task_has_test_cases:
            skipped_reasons.append("для задания не заданы автотесты")
        new_submission.test_result = format_test_result(
            0,
            0,
            summary=(
                "Автоматическая проверка пропущена: "
                f"{', '.join(skipped_reasons)}"
            ),
        )
        await db.commit()
        await db.refresh(new_submission)

    return new_submission


@router.get("/me", response_model=List[StudentSubmissionRead])
@PermissionChecker(UserRole.student)
async def get_my_submissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.inline_comments))
        .where(Submission.user_id == current_user.id)
        .order_by(Submission.created_at.desc())
    )
    return result.scalars().all()


@router.get("/task/{task_id}", response_model=List[TeacherSubmissionRead])
@PermissionChecker(UserRole.teacher, UserRole.admin)
async def get_submissions_by_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задание не найдено",
        )

    if current_user.role == UserRole.teacher and task.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете просматривать решения только для своих заданий",
        )

    result = await db.execute(
        select(Submission)
        .options(
            joinedload(Submission.user),
            selectinload(Submission.inline_comments),
        )
        .where(Submission.task_id == task_id)
        .order_by(Submission.created_at.desc())
    )
    return [
        serialize_teacher_submission(submission)
        for submission in result.scalars().all()
    ]


@router.get("/{submission_id}", response_model=TeacherSubmissionRead)
@PermissionChecker(UserRole.teacher, UserRole.admin)
async def get_submission_by_id(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Submission)
        .options(
            joinedload(Submission.user),
            selectinload(Submission.inline_comments),
            joinedload(Submission.task),
        )
        .where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Решение не найдено",
        )

    if (
        current_user.role == UserRole.teacher
        and submission.task.created_by_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете просматривать решения только для своих заданий",
        )

    return serialize_teacher_submission(submission)


@router.patch("/{submission_id}", response_model=TeacherSubmissionRead)
@PermissionChecker(UserRole.teacher, UserRole.admin)
async def grade_submission(
    submission_id: int,
    update_data: TeacherSubmissionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Submission)
        .options(
            joinedload(Submission.user),
            joinedload(Submission.task),
            selectinload(Submission.inline_comments),
        )
        .where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Решение не найдено",
        )

    if (
        current_user.role == UserRole.teacher
        and submission.task.created_by_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете оценивать решения только для своих заданий",
        )

    submission.grade = update_data.grade
    submission.final_comment = update_data.final_comment
    submission.status = (
        SubmissionStatus.passed
        if update_data.grade >= 25
        else SubmissionStatus.failed
    )

    await db.commit()
    await db.refresh(submission)
    return serialize_teacher_submission(submission)
