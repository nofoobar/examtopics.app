from enum import Enum
from typing import Optional
from sqlmodel import Field, Relationship

from .base import BaseModel


class AdPosition(str, Enum):
    banner  = "banner"    # top/bottom of page
    sidebar = "sidebar"   # beside question list
    inline  = "inline"    # between questions


class Advertisement(BaseModel, table=True):
    """
    An advertisement unit.
    - Generic ads (is_generic_ad=True) appear site-wide; exam_id should be null.
    - Exam-specific ads (is_generic_ad=False) are shown only on that exam's pages.
    """
    __tablename__ = "advertisement"

    # ── Identity ──────────────────────────────────────────────────────────
    title: str = Field(max_length=255, index=True)          # admin label only
    image_url: str = Field(max_length=500)
    alt_text: Optional[str] = Field(default=None, max_length=255)  # img alt
    ad_text: Optional[str] = Field(default=None, max_length=500)   # tagline shown beside the image

    # ── Destination ───────────────────────────────────────────────────────
    link: str = Field(max_length=500)
    notify_on_click: bool = Field(default=False)             # ping webhook / log

    # ── Targeting ─────────────────────────────────────────────────────────
    is_generic_ad: bool = Field(default=True)                # site-wide vs exam
    exam_id: Optional[int] = Field(default=None, foreign_key="exam.id", index=True)
    exam: Optional["Exam"] = Relationship(back_populates="advertisements")  # type: ignore[name-defined]
    position: AdPosition = Field(default=AdPosition.banner)

    # ── Stats ─────────────────────────────────────────────────────────────
    click_count: int = Field(default=0)

    # ── Scheduling ────────────────────────────────────────────────────────
    starts_at: Optional[str] = Field(default=None)           # ISO datetime string
    ends_at: Optional[str] = Field(default=None)             # ISO datetime string

    # ── Status ────────────────────────────────────────────────────────────
    is_active: bool = Field(default=True)
