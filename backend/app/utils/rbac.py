from functools import wraps

from app.models.user import UserRole
from fastapi import HTTPException, status


class PermissionChecker:
    """Декоратор для проверки ролей пользователя"""
    def __init__(self, *roles: UserRole):
        self.roles = roles

    def __call__(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("current_user")  # Получаем текущего пользователя
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Требуется аутентификация"
                )

            if user.role is UserRole.admin:  # Админ всегда имеет доступ ко всему
                return await func(*args, **kwargs)

            if user.role not in self.roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Недостаточно прав для доступа"
                )
            return await func(*args, **kwargs)
        return wrapper
