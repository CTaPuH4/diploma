from sqlalchemy import select

from app.models.test_case import TestCase as TaskTestCase
from app.models.user import UserRole
from tests.factories import (
    create_group,
    create_task,
    create_test_case,
    create_user,
    make_auth_headers,
)


async def test_teacher_can_create_task_with_test_cases(client, session_factory):
    async with session_factory() as session:
        group = await create_group(session, slug="iu7-33b", title="IU7-33B")
        teacher = await create_user(
            session,
            username="teacher-tasks",
            full_name="Teacher Tasks",
            role=UserRole.teacher,
        )
        headers = make_auth_headers(teacher)

    response = await client.post(
        "/tasks/",
        headers=headers,
        json={
            "title": "Sum numbers",
            "text": "Return the sum of two integers.",
            "group_id": group.id,
            "test_cases": [
                {"input": "1 2", "output": "3", "is_hidden": False},
                {"input": "10 5", "output": "15", "is_hidden": True},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Sum numbers"
    assert body["group_id"] == group.id

    async with session_factory() as session:
        result = await session.execute(
            select(TaskTestCase).where(TaskTestCase.task_id == body["id"])
        )
        test_cases = result.scalars().all()
        assert len(test_cases) == 2
        assert {test_case.is_hidden for test_case in test_cases} == {False, True}


async def test_student_sees_only_visible_test_cases_in_task_detail(
    client, session_factory
):
    async with session_factory() as session:
        group = await create_group(session, slug="iu7-34b", title="IU7-34B")
        teacher = await create_user(
            session,
            username="teacher-detail",
            full_name="Teacher Detail",
            role=UserRole.teacher,
        )
        student = await create_user(
            session,
            username="student-detail",
            full_name="Student Detail",
            role=UserRole.student,
            group_id=group.id,
        )
        task = await create_task(
            session,
            title="Visible tests",
            text="Task text",
            group_id=group.id,
            created_by_id=teacher.id,
        )
        await create_test_case(
            session,
            task_id=task.id,
            input_data="1",
            output_data="1",
            is_hidden=False,
        )
        await create_test_case(
            session,
            task_id=task.id,
            input_data="2",
            output_data="4",
            is_hidden=True,
        )
        headers = make_auth_headers(student)

    response = await client.get(f"/tasks/{task.id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body["test_cases"]) == 1
    assert body["test_cases"][0]["is_hidden"] is False
