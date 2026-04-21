from typing import Optional

from app.models.user import UserRole
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None


class UserRegister(BaseModel):
    username: str
    full_name: str
    password: str
    role: UserRole = UserRole.student
    group_id: Optional[int] = None


class UserLogin(BaseModel):
    username: str
    password: str
