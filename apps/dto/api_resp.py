"""Standard API response wrapper for Jira Logger."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class APIResponse(BaseModel):
    """Standard API response envelope."""
    data: Any = None
    errors: Optional[Any] = None
    success: bool = True
    message: str = "Success."
    statusCode: int = 200
    requestTime: str = ""

    def model_post_init(self, __context):
        if not self.requestTime:
            self.requestTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class PaginatedResponse(BaseModel):
    """Paginated API response envelope."""
    data: Any = None
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0
    success: bool = True
    message: str = "Success."
    statusCode: int = 200
    requestTime: str = ""

    def model_post_init(self, __context):
        if not self.requestTime:
            self.requestTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.total > 0 and self.page_size > 0:
            self.total_pages = (self.total + self.page_size - 1) // self.page_size
