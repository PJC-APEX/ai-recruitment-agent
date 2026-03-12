"""API routes for resume scoring."""

import logging
from fastapi import APIRouter, HTTPException, Depends
from app.dependencies import get_scoring_pipeline
from app.rag.scoring_pipeline import ScoringPipeline
from app.models.request_models import ScoreResumeRequest
from app.models.response_models import ScoreResumeResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/score-resume", response_model=ScoreResumeResponse)
async def score_resume(
    request: ScoreResumeRequest,
    scoring_pipeline: ScoringPipeline = Depends(get_scoring_pipeline)
):
    """Score a resume against a job description.
    
    Args:
        request: Score request with resume text and job description
        scoring_pipeline: Scoring pipeline
        
    Returns:
        Scoring results with match score and analysis
    """
    try:
        logger.info("Scoring resume against job description")
        
        # Validate inputs
        if not request.resume_text or len(request.resume_text) < 50:
            raise HTTPException(
                status_code=400,
                detail="Resume text is too short or empty"
            )
        
        if not request.job_description or len(request.job_description) < 20:
            raise HTTPException(
                status_code=400,
                detail="Job description is too short or empty"
            )
        
        # Score the resume
        score_result = await scoring_pipeline.score_resume(
            resume_text=request.resume_text,
            job_description=request.job_description
        )
        
        return ScoreResumeResponse(
            score_result=score_result,
            resume_file=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scoring resume: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")
