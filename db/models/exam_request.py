from enum import Enum
from typing import Optional

from sqlmodel import Field

from .base import BaseModel


class ExamRequestStatus(str, Enum):
    pending    = "pending"
    in_review  = "in_review"
    completed  = "completed"


class ExamRequest(BaseModel, table=True):
    """User-submitted request for an exam to be added to the platform."""
    __tablename__ = "exam_request"

    exam_name: str = Field(max_length=255, index=True)
    email: str = Field(max_length=254, index=True)
    message: Optional[str] = Field(default=None)
    status: ExamRequestStatus = Field(default=ExamRequestStatus.pending, index=True)
