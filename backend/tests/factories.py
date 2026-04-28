from datetime import UTC, datetime

from app.models.group import Group
from app.models.inline_comment import InlineComment
from app.models.submission import Submission, SubmissionLanguage, SubmissionStatus
from app.models.task import Task
from app.models.test_case import TestCase
from app.models.user import User, UserRole
from app.utils.security import create_access_token, get_password_hash
from sqlalchemy.ext.asyncio import AsyncSession


async def create_group(
    session: AsyncSession,
    *,
    slug: str,
    title: str,
) -> Group:
    group = Group(slug=slug, title=title)
    session.add(group)
    await session.commit()
    await session.refresh(group)
    return group


async def create_user(
    session: AsyncSession,
    *,
    username: str,
    full_name: str,
    role: UserRole,
    password: str = "secret123",
    group_id: int | None = None,
) -> User:
    user = User(
        username=username,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        role=role,
        group_id=group_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_task(
    session: AsyncSession,
    *,
    title: str,
    text: str,
    group_id: int,
    created_by_id: int,
    deadline: datetime | None = None,
) -> Task:
    task = Task(
        title=title,
        text=text,
        deadline=deadline or datetime(2026, 5, 1, tzinfo=UTC),
        group_id=group_id,
        created_by_id=created_by_id,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def create_test_case(
    session: AsyncSession,
    *,
    task_id: int,
    input_data: str,
    output_data: str,
    is_hidden: bool = False,
) -> TestCase:
    test_case = TestCase(
        task_id=task_id,
        input=input_data,
        output=output_data,
        is_hidden=is_hidden,
    )
    session.add(test_case)
    await session.commit()
    await session.refresh(test_case)
    return test_case


async def create_submission(
    session: AsyncSession,
    *,
    task_id: int,
    user_id: int,
    code: str,
    language: SubmissionLanguage = SubmissionLanguage.python,
    status: SubmissionStatus = SubmissionStatus.on_review,
    test_result: str | None = None,
    llm_comment: str | None = None,
) -> Submission:
    submission = Submission(
        task_id=task_id,
        user_id=user_id,
        code=code,
        language=language,
        status=status,
        test_result=test_result,
        llm_comment=llm_comment,
        llm_completed=True,
    )
    session.add(submission)
    await session.commit()
    await session.refresh(submission)
    return submission


async def create_inline_comment(
    session: AsyncSession,
    *,
    submission_id: int,
    line_start: int,
    text: str,
    line_end: int | None = None,
) -> InlineComment:
    comment = InlineComment(
        submission_id=submission_id,
        line_start=line_start,
        line_end=line_end or line_start,
        text=text,
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    return comment


def make_auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(
        {
            "sub": user.username,
            "role": user.role.value,
        }
    )
    return {"Authorization": f"Bearer {token}"}
