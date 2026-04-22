from app.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    deadline = Column(DateTime, nullable=True)

    group_id = Column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Связи
    submissions = relationship(
        "Submission", back_populates="task", cascade="all, delete-orphan"
    )
    test_cases = relationship(
        "TestCase", back_populates="task", cascade="all, delete-orphan"
    )
    group = relationship("Group", foreign_keys=[group_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<Task {self.title} (group {self.group_id})>"
