from __future__ import annotations

from datetime import datetime

from app.database import Base
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    created_by_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    submissions: Mapped[list["Submission"]] = relationship(
        "Submission", back_populates="task", cascade="all, delete-orphan"
    )
    test_cases: Mapped[list["TestCase"]] = relationship(
        "TestCase", back_populates="task", cascade="all, delete-orphan"
    )
    group: Mapped["Group"] = relationship("Group", foreign_keys=[group_id])
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<Task {self.title} (group {self.group_id})>"
