from enum import Enum
from typing import Any, Optional

from sqlmodel import Field, Column
from sqlalchemy import JSON

from .base import BaseModel


class JobStatus(str, Enum):
    pending  = "pending"
    running  = "running"
    done     = "done"
    failed   = "failed"


class GenerationJob(BaseModel, table=True):
    """Tracks the async exam-generation background task."""
    __tablename__ = "generation_job"

    # Human-readable label shown in UI
    exam_name: str = Field(max_length=255)

    # Lifecycle
    status: JobStatus = Field(default=JobStatus.pending, index=True)
    error: Optional[str] = Field(default=None)

    # Progress counters (questions generated / total questions to generate)
    completed_steps: int = Field(default=0)
    total_steps: int = Field(default=0)

    # Set once the exam is persisted
    result_exam_id: Optional[int] = Field(default=None, foreign_key="exam.id")

    # Full form payload stored so the background task can reconstruct everything
    config: dict[str, Any] = Field(default={}, sa_column=Column(JSON))
