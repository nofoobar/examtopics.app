from typing import Optional
from sqlmodel import Field

from .base import BaseModel


class Search(BaseModel, table=True):
    """Log of user search queries — useful for analytics and autocomplete."""
    __tablename__ = "search"

    search_term: str = Field(max_length=255, index=True)
    results_count: int = Field(default=0)
    ip_address: Optional[str] = Field(default=None, max_length=45)  # supports IPv6
