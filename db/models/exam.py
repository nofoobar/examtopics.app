from enum import Enum
from typing import Any, Optional
from sqlmodel import Field, Relationship, Column
from sqlalchemy import JSON

from .base import BaseModel


# ---------------------------------------------------------------------------
# Vendor  (e.g. Amazon, Microsoft, CompTIA, Google)
# ---------------------------------------------------------------------------

class Vendor(BaseModel, table=True):
    """Certification body / exam issuer."""
    __tablename__ = "vendor"

    name: str = Field(max_length=255, index=True)
    slug: str = Field(max_length=255, unique=True, index=True)
    description: Optional[str] = Field(default=None)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    is_popular: bool = Field(default=False)

    exams: list["Exam"] = Relationship(back_populates="vendor")


# ---------------------------------------------------------------------------
# Exam  (e.g. AWS SAA-C03, AZ-900, CompTIA Security+)
# ---------------------------------------------------------------------------

class Exam(BaseModel, table=True):
    """A certification exam offered by a Vendor."""
    __tablename__ = "exam"

    vendor_id: int = Field(foreign_key="vendor.id", index=True)
    vendor: Vendor = Relationship(back_populates="exams")
    managed_order_id: int = Field(default=0)

    name: str = Field(max_length=255, index=True)
    exam_code: Optional[str] = Field(default=None, max_length=50)
    slug: str = Field(max_length=255, unique=True, index=True)
    description: Optional[str] = Field(default=None)
    short_description: Optional[str] = Field(default=None, max_length=255)
    thumbnail_url: Optional[str] = Field(default=None, max_length=500)
    is_featured: bool = Field(default=False)
    is_active: bool = Field(default=True)

    tests: list["Test"] = Relationship(
        back_populates="exam",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    advertisements: list["Advertisement"] = Relationship(back_populates="exam")  # type: ignore[name-defined]


# ---------------------------------------------------------------------------
# Test  (a numbered practice set within an exam, e.g. "Practice Test 1")
# ---------------------------------------------------------------------------

class Test(BaseModel, table=True):
    """A practice test / question set that belongs to an Exam."""
    __tablename__ = "test"

    exam_id: int = Field(foreign_key="exam.id", index=True)
    exam: Exam = Relationship(back_populates="tests")

    name: str = Field(max_length=255)
    slug: str = Field(max_length=255, unique=True, index=True)
    # sources: list of URL strings scraped / referenced
    sources: list[Any] = Field(default=[], sa_column=Column(JSON))
    is_active: bool = Field(default=True)

    questions: list["Question"] = Relationship(
        back_populates="test",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------

class QuestionType(str, Enum):
    multiple_choice = "multiple-choice"
    multi_select    = "multi-select"


class Question(BaseModel, table=True):
    """A single exam question belonging to a Test."""
    __tablename__ = "question"

    test_id: int = Field(foreign_key="test.id", index=True)
    test: Test = Relationship(back_populates="questions")

    question: str
    question_type: QuestionType = Field(default=QuestionType.multiple_choice)

    options: dict[str, Any]         = Field(default={}, sa_column=Column(JSON))
    correct_options: list[Any]      = Field(default=[], sa_column=Column(JSON))
    explanations: dict[str, Any]    = Field(default={}, sa_column=Column(JSON))
    overall_explanation: Optional[str] = Field(default=None)

    # Optional extras
    llm_model: Optional[str] = Field(default=None, max_length=255)
    domain: Optional[str] = Field(default=None, max_length=255)
    source: Optional[str] = Field(default=None, max_length=500)
    extra_metadata: dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    is_active: bool = Field(default=True)
