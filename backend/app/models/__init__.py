"""Initialize models package."""

from app.models.request_models import (
    SearchRequest,
    ScoreResumeRequest,
    ChatRequest,
    RankCandidatesRequest
)
from app.models.response_models import (
    ResumeUploadResponse,
    SearchResponse,
    ScoreResumeResponse,
    RankingResponse,
    ChatResponse,
    CandidateResult,
    RankedCandidate
)

__all__ = [
    "SearchRequest",
    "ScoreResumeRequest",
    "ChatRequest",
    "RankCandidatesRequest",
    "ResumeUploadResponse",
    "SearchResponse",
    "ScoreResumeResponse",
    "RankingResponse",
    "ChatResponse",
    "CandidateResult",
    "RankedCandidate",
]
