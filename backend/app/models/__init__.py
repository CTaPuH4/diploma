# Экспортируем Base из database
from app.database import Base

from .group import Group
from .inline_comment import InlineComment
from .submission import Submission, SubmissionStatus
from .task import Task
from .test_case import TestCase
from .user import User, UserRole

__all__ = [
    "User", "UserRole", "Group", "Task", "Submission", "SubmissionStatus",
    "TestCase", "InlineComment", "Base"
]





a, b = map(int, input().split())
print(a + b)