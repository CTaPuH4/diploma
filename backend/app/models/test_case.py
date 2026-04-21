from app.database import Base
from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)

    input = Column(Text, nullable=False)
    output = Column(Text, nullable=False)

    task = relationship("Task", back_populates="test_cases")

    def __repr__(self):
        return f"<TestCase {self.id} for task {self.task_id}>"
