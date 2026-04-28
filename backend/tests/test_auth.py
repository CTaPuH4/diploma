from sqlalchemy import select

from app.models.user import User, UserRole
from tests.factories import create_user


async def test_register_creates_student_and_returns_token(client, session_factory):
    response = await client.post(
        "/auth/register",
        json={
            "username": "new-student",
            "full_name": "New Student",
            "password": "strong-pass",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.username == "new-student")
        )
        user = result.scalar_one()
        assert user.full_name == "New Student"
        assert user.role == UserRole.student
        assert user.group_id is None


async def test_login_rejects_invalid_password(client, session_factory):
    async with session_factory() as session:
        await create_user(
            session,
            username="student-login",
            full_name="Student Login",
            role=UserRole.student,
            password="correct-password",
        )

    response = await client.post(
        "/auth/login",
        data={
            "username": "student-login",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный логин или пароль"
