"""Models for long-term memory management."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class MemoryCreateRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    memory_type: str = Field(default="fact", min_length=1)
    importance: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=1.0, ge=0, le=1)
    source_session_id: Optional[str] = None
    expires_at: Optional[datetime] = None

class MemoryResponse(MemoryCreateRequest):
    id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
