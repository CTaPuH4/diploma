from sqlalchemy import select

from app.models.user import User, UserRole
from tests.factories import create_group, create_user, make_auth_headers


async def test_user_can_update_own_profile(client, session_factory):
    async with session_factory() as session:
        old_group = await create_group(session, slug="iu7-35b", title="IU7-35B")
        new_group = await create_group(session, slug="iu7-36b", title="IU7-36B")
        student = await create_user(
            session,
            username="student-profile",
            full_name="Old Name",
            role=UserRole.student,
            group_id=old_group.id,
        )
        headers = make_auth_headers(student)

    response = await client.patch(
        "/users/me",
        headers=headers,
        json={
            "full_name": "Updated Name",
            "group_id": new_group.id,
        },
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Name"
    assert response.json()["group_id"] == new_group.id

    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.username == "student-profile")
        )
        user = result.scalar_one()
        assert user.full_name == "Updated Name"
        assert user.group_id == new_group.id


async def test_change_password_rejects_wrong_current_password(client, session_factory):
    async with session_factory() as session:
        student = await create_user(
            session,
            username="student-password",
            full_name="Student Password",
            role=UserRole.student,
            password="correct-password",
        )
        headers = make_auth_headers(student)

    response = await client.post(
        "/users/change-password",
        headers=headers,
        json={
            "old_password": "wrong-password",
            "new_password": "new-password",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid current password"
