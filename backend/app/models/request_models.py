"""Request models for API endpoints."""

from pydantic import BaseModel, Field
from typing import Optional


class SearchRequest(BaseModel):
    """Request model for resume search."""
    query: str = Field(..., description="Natural language query for searching resumes")
    top_k: Optional[int] = Field(5, description="Number of results to return")


class ScoreResumeRequest(BaseModel):
    """Request model for scoring a resume against a job description."""
    resume_text: str = Field(..., description="Resume text content")
    job_description: str = Field(..., description="Job description to match against")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Stable conversation id for short-term memory")
    chat_history: Optional[list] = Field(default_factory=list, description="Previous conversation history")


class RankCandidatesRequest(BaseModel):
    """Request model for ranking candidates."""
    job_description: str = Field(..., description="Job description")
    query: Optional[str] = Field(None, description="Search query to filter candidates")
    top_k: Optional[int] = Field(5, description="Number of candidates to rank")
