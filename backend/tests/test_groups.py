from app.models.user import UserRole
from tests.factories import create_group, create_user, make_auth_headers

INSUFFICIENT_PERMISSIONS_DETAIL = (
    "\u041d\u0435\u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u043e "
    "\u043f\u0440\u0430\u0432"
)


async def test_admin_can_create_group(client, session_factory):
    async with session_factory() as session:
        admin = await create_user(
            session,
            username="admin-groups",
            full_name="Admin Groups",
            role=UserRole.admin,
        )
        headers = make_auth_headers(admin)

    response = await client.post(
        "/groups/",
        headers=headers,
        json={"slug": "iu7-41b", "title": "IU7-41B"},
    )

    assert response.status_code == 200
    assert response.json()["slug"] == "iu7-41b"


async def test_student_cannot_create_group(client, session_factory):
    async with session_factory() as session:
        group = await create_group(session, slug="iu7-32b", title="IU7-32B")
        student = await create_user(
            session,
            username="student-groups",
            full_name="Student Groups",
            role=UserRole.student,
            group_id=group.id,
        )
        headers = make_auth_headers(student)

    response = await client.post(
        "/groups/",
        headers=headers,
        json={"slug": "iu7-42b", "title": "IU7-42B"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == INSUFFICIENT_PERMISSIONS_DETAIL
