from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ExamResponse(BaseModel):
    id: int
    name: str
    exam_code: Optional[str]
    slug: str
    short_description: Optional[str]
    is_featured: bool
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VendorResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class VendorWithExams(VendorResponse):
    exams: List[ExamResponse] = []
