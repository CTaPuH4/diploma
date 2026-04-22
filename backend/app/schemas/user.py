from typing import Optional

from app.models.user import UserRole
from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    full_name: str
    password: str
    role: UserRole = UserRole.student
    group_id: Optional[int] = None


class UserRead(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    group_id: Optional[int] = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdateSelf(BaseModel):
    full_name: Optional[str] = None
    group_id: Optional[int] = None


class UserUpdate(UserUpdateSelf):
    role: Optional[UserRole] = None


class UserChangePassword(BaseModel):
    old_password: str
    new_password: str
