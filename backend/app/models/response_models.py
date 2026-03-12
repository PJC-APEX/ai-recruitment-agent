"""Response models for API endpoints."""

from pydantic import BaseModel, Field
from typing import List, Optional, Any


class ResumeMetadata(BaseModel):
    """Metadata for a resume."""
    candidate_name: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    years_experience: Optional[int] = None
    file_name: str


class ResumeUploadResponse(BaseModel):
    """Response model for resume upload."""
    success: bool
    message: str
    file_name: str
    chunks_created: int
    metadata: ResumeMetadata


class CandidateResult(BaseModel):
    """A single candidate result."""
    candidate_name: Optional[str] = None
    file_name: str
    skills: List[str] = Field(default_factory=list)
    years_experience: Optional[int] = None
    relevance_score: float = Field(..., description="Similarity score (0-1)")
    resume_snippet: Optional[str] = None


class SearchResponse(BaseModel):
    """Response model for resume search."""
    query: str
    results: List[CandidateResult]
    total_results: int


class ScoreResult(BaseModel):
    """Scoring result for a resume."""
    match_score: int = Field(..., ge=0, le=100, description="Match score between 0-100")
    matching_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    experience_match: bool
    summary: str


class ScoreResumeResponse(BaseModel):
    """Response model for resume scoring."""
    score_result: ScoreResult
    resume_file: Optional[str] = None


class RankedCandidate(BaseModel):
    """A ranked candidate with scoring information."""
    rank: int
    candidate_name: Optional[str] = None
    file_name: str
    match_score: int = Field(..., ge=0, le=100)
    matching_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    summary: str


class RankingResponse(BaseModel):
    """Response model for candidate ranking."""
    job_description: str
    ranked_candidates: List[RankedCandidate]
    total_evaluated: int


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    message: str
    response: str
    data: Optional[Any] = None
