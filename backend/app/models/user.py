import enum

from app.database import Base
from sqlalchemy import Column
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import relationship


class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.student)
    group_id = Column(
        Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )

    # Связи
    submissions = relationship(
        "Submission", back_populates="user", cascade="all, delete-orphan"
    )
    group = relationship("Group", back_populates="students")

    def __repr__(self):
        return f"<User {self.username} ({self.role.value})>"
