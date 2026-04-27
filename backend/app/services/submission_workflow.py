from app.database import AsyncSessionLocal
from app.models.submission import Submission, SubmissionLanguage, SubmissionStatus
from app.models.test_case import TestCase
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def should_run_judge(language: SubmissionLanguage, has_test_cases: bool) -> bool:
    return language != SubmissionLanguage.other and has_test_cases


async def has_test_cases(db: AsyncSession, task_id: int) -> bool:
    result = await db.execute(
        select(func.count()).select_from(TestCase).where(TestCase.task_id == task_id)
    )
    return bool(result.scalar_one())


async def update_submission_review_status(
    db: AsyncSession,
    submission: Submission,
    *,
    has_auto_tests: bool,
) -> None:
    if submission.status in {SubmissionStatus.passed, SubmissionStatus.failed}:
        return

    judge_required = should_run_judge(submission.language, has_auto_tests)
    llm_ready = submission.llm_completed
    judge_ready = (not judge_required) or (submission.test_result is not None)

    submission.status = (
        SubmissionStatus.on_review
        if llm_ready and judge_ready
        else SubmissionStatus.analyzing
    )


async def finalize_submission_review_status(submission_id: int) -> None:
    async with AsyncSessionLocal() as db:
        submission = await db.get(Submission, submission_id)
        if submission is None:
            return

        await update_submission_review_status(
            db,
            submission,
            has_auto_tests=await has_test_cases(db, submission.task_id),
        )
        await db.commit()
