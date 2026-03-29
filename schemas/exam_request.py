from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

from db.models.exam_request import ExamRequestStatus


class ExamRequestCreate(BaseModel):
    exam_name: str
    email: EmailStr
    message: Optional[str] = None


class ExamRequestResponse(BaseModel):
    id: int
    exam_name: str
    email: str
    message: Optional[str]
    status: ExamRequestStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
