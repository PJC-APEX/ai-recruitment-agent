"""Ranking service for candidates using LLM."""

import logging
from typing import List, Dict, Any
from app.llm.llm_client import LLMClient
from app.llm.prompt_templates import RANKING_PROMPT

logger = logging.getLogger(__name__)


class RankingService:
    """Service for ranking candidates using LLM."""
    
    def __init__(self, llm_client: LLMClient):
        """Initialize ranking service.
        
        Args:
            llm_client: LLM client for generating rankings
        """
        self.llm_client = llm_client
        self.logger = logger
    
    async def rank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        job_description: str
    ) -> List[Dict[str, Any]]:
        """Rank candidates based on job description.
        
        Args:
            candidates: List of candidate dictionaries with resume info
            job_description: Job description to rank against
            
        Returns:
            List of ranked candidates with scores
        """
        try:
            ranked_results = []
            
            for idx, candidate in enumerate(candidates, 1):
                # Create prompt for this candidate
                prompt = RANKING_PROMPT.format(
                    job_description=job_description,
                    resume_text=candidate.get("resume_text", ""),
                    candidate_name=candidate.get("candidate_name", "Unknown")
                )
                
                # Get LLM response
                response = await self.llm_client.generate_structured_output(
                    prompt=prompt,
                    schema={
                        "match_score": "int (0-100)",
                        "matching_skills": "list of strings",
                        "missing_skills": "list of strings",
                        "summary": "string"
                    }
                )
                
                ranked_results.append({
                    "rank": idx,
                    "candidate_name": candidate.get("candidate_name"),
                    "file_name": candidate.get("file_name"),
                    "match_score": response.get("match_score", 0),
                    "matching_skills": response.get("matching_skills", []),
                    "missing_skills": response.get("missing_skills", []),
                    "summary": response.get("summary", "")
                })
            
            # Sort by match score
            ranked_results.sort(key=lambda x: x["match_score"], reverse=True)
            
            # Update ranks after sorting
            for idx, result in enumerate(ranked_results, 1):
                result["rank"] = idx
            
            self.logger.info(f"Ranked {len(ranked_results)} candidates")
            return ranked_results
            
        except Exception as e:
            self.logger.error(f"Error ranking candidates: {str(e)}")
            raise Exception(f"Failed to rank candidates: {str(e)}")
