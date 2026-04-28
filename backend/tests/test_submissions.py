from unittest.mock import patch

from sqlalchemy import select

from app.models.submission import Submission, SubmissionLanguage, SubmissionStatus
from app.models.user import UserRole
from tests.factories import (
    create_group,
    create_inline_comment,
    create_submission,
    create_task,
    create_test_case,
    create_user,
    make_auth_headers,
)

JUDGE_SKIPPED_DETAIL = (
    "\u0410\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0430\u044f "
    "\u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 "
    "\u043f\u0440\u043e\u043f\u0443\u0449\u0435\u043d\u0430"
)
UNSUPPORTED_LANGUAGE_DETAIL = (
    "\u043d\u0435 "
    "\u043f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u0435\u0442\u0441\u044f "
    "\u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u043e\u0439 "
    "\u043f\u0440\u043e\u0432\u0435\u0440\u043a\u043e\u0439"
)


async def noop_background_job(*args, **kwargs):
    return None


async def test_student_can_create_submission_and_skip_judge_for_other_language(
    client, session_factory
):
    async with session_factory() as session:
        group = await create_group(session, slug="iu7-37b", title="IU7-37B")
        teacher = await create_user(
            session,
            username="teacher-submission",
            full_name="Teacher Submission",
            role=UserRole.teacher,
        )
        student = await create_user(
            session,
            username="student-submission",
            full_name="Student Submission",
            role=UserRole.student,
            group_id=group.id,
        )
        task = await create_task(
            session,
            title="Judge skip",
            text="Task text",
            group_id=group.id,
            created_by_id=teacher.id,
        )
        await create_test_case(
            session,
            task_id=task.id,
            input_data="1 2",
            output_data="3",
        )
        headers = make_auth_headers(student)

    with (
        patch(
            "app.routers.submissions.analyze_submission",
            side_effect=noop_background_job,
        ),
        patch(
            "app.routers.submissions.judge_submission",
            side_effect=noop_background_job,
        ),
    ):
        response = await client.post(
            "/submissions/",
            headers=headers,
            json={
                "task_id": task.id,
                "code": "print('hello')",
                "language": SubmissionLanguage.other.value,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == SubmissionStatus.analyzing.value

    async with session_factory() as session:
        result = await session.execute(
            select(Submission).where(Submission.id == body["id"])
        )
        submission = result.scalar_one()
        assert JUDGE_SKIPPED_DETAIL in submission.test_result
        assert UNSUPPORTED_LANGUAGE_DETAIL in submission.test_result


async def test_teacher_can_grade_submission(client, session_factory):
    async with session_factory() as session:
        group = await create_group(session, slug="iu7-38b", title="IU7-38B")
        teacher = await create_user(
            session,
            username="teacher-grade",
            full_name="Teacher Grade",
            role=UserRole.teacher,
        )
        student = await create_user(
            session,
            username="student-grade",
            full_name="Student Grade",
            role=UserRole.student,
            group_id=group.id,
        )
        task = await create_task(
            session,
            title="Check solution",
            text="Task text",
            group_id=group.id,
            created_by_id=teacher.id,
        )
        submission = await create_submission(
            session,
            task_id=task.id,
            user_id=student.id,
            code="print(42)",
            language=SubmissionLanguage.python,
            status=SubmissionStatus.on_review,
        )
        await create_inline_comment(
            session,
            submission_id=submission.id,
            line_start=1,
            text="Needs a clearer explanation.",
        )
        headers = make_auth_headers(teacher)

    response = await client.patch(
        f"/submissions/{submission.id}",
        headers=headers,
        json={
            "grade": 40,
            "final_comment": "Good solution, but readability can be improved.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["grade"] == 40
    assert body["status"] == SubmissionStatus.passed.value
    assert body["final_comment"] == "Good solution, but readability can be improved."
