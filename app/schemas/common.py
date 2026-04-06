"""Common Pydantic schemas."""
from pydantic import BaseModel
from typing import List


class BulkDeleteRequest(BaseModel):
    ids: List[int]
