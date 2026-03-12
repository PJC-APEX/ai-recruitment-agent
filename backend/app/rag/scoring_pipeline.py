"""RAG scoring pipeline for evaluating resumes."""

import logging
from typing import Dict, Any
from app.llm.llm_client import LLMClient
from app.llm.prompt_templates import RESUME_SCORING_PROMPT
from app.models.response_models import ScoreResult

logger = logging.getLogger(__name__)


class ScoringPipeline:
    """Pipeline for scoring resumes against job descriptions."""
    
    def __init__(self, llm_client: LLMClient):
        """Initialize scoring pipeline.
        
        Args:
            llm_client: LLM client for generating scores
        """
        self.llm_client = llm_client
        self.logger = logger
    
    async def score_resume(
        self,
        resume_text: str,
        job_description: str
    ) -> ScoreResult:
        """Score a resume against a job description.
        
        Args:
            resume_text: Full text of the resume
            job_description: Job description to match against
            
        Returns:
            ScoreResult with detailed scoring information
        """
        try:
            # Create scoring prompt
            prompt = RESUME_SCORING_PROMPT.format(
                job_description=job_description,
                resume_text=resume_text
            )
            
            # Define expected schema
            schema = {
                "match_score": "int (0-100)",
                "matching_skills": "list of strings",
                "missing_skills": "list of strings",
                "experience_match": "boolean",
                "summary": "string"
            }
            
            # Get structured response from LLM
            response = await self.llm_client.generate_structured_output(
                prompt=prompt,
                schema=schema,
                system_message="You are an expert recruiter providing objective resume evaluations."
            )
            
            # Validate and normalize response
            score_result = ScoreResult(
                match_score=max(0, min(100, response.get("match_score", 0))),
                matching_skills=response.get("matching_skills", []),
                missing_skills=response.get("missing_skills", []),
                experience_match=response.get("experience_match", False),
                summary=response.get("summary", "")
            )
            
            self.logger.info(f"Generated resume score: {score_result.match_score}")
            return score_result
            
        except Exception as e:
            self.logger.error(f"Error in scoring pipeline: {str(e)}")
            raise Exception(f"Failed to score resume: {str(e)}")
    
    async def batch_score_resumes(
        self,
        resumes: list[Dict[str, str]],
        job_description: str
    ) -> list[ScoreResult]:
        """Score multiple resumes against a job description.
        
        Args:
            resumes: List of resume dictionaries with 'text' and 'filename'
            job_description: Job description to match against
            
        Returns:
            List of ScoreResult objects
        """
        try:
            results = []
            
            for resume in resumes:
                score_result = await self.score_resume(
                    resume_text=resume["text"],
                    job_description=job_description
                )
                results.append(score_result)
            
            self.logger.info(f"Scored {len(results)} resumes")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in batch scoring: {str(e)}")
            raise Exception(f"Failed to batch score resumes: {str(e)}")
