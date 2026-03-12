"""RAG retrieval pipeline for searching resumes."""

import logging
from typing import List, Dict, Any, Optional
from app.services.vector_store_service import VectorStoreService
from app.models.response_models import CandidateResult

logger = logging.getLogger(__name__)


class RetrievalPipeline:
    """Pipeline for retrieving relevant resumes using RAG."""
    
    def __init__(self, vector_store: VectorStoreService, top_k: int = 5):
        """Initialize retrieval pipeline.
        
        Args:
            vector_store: Vector store service
            top_k: Default number of results to return
        """
        self.vector_store = vector_store
        self.top_k = top_k
        self.logger = logger
    
    async def search_resumes(
        self,
        query: str,
        top_k: Optional[int] = None,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[CandidateResult]:
        """Search for relevant resumes.
        
        Args:
            query: Natural language search query
            top_k: Number of results to return
            metadata_filter: Optional metadata filter
            
        Returns:
            List of candidate results
        """
        try:
            k = top_k or self.top_k
            
            # Perform vector search
            results = await self.vector_store.search(
                query=query,
                top_k=k,
                filter_metadata=metadata_filter
            )
            
            # Group results by file_name to avoid duplicate candidates
            candidates_map = {}
            
            for doc, metadata, distance, doc_id in zip(
                results["documents"],
                results["metadatas"],
                results["distances"],
                results["ids"]
            ):
                file_name = metadata.get("file_name", "unknown")
                
                # Calculate relevance score (1 - normalized distance)
                # ChromaDB uses cosine distance, so lower is better
                relevance_score = 1.0 - (distance / 2.0)  # Normalize to 0-1
                
                if file_name not in candidates_map:
                    candidates_map[file_name] = {
                        "candidate_name": metadata.get("candidate_name"),
                        "file_name": file_name,
                        "skills": metadata.get("skills", []),
                        "years_experience": metadata.get("years_experience"),
                        "relevance_score": relevance_score,
                        "resume_snippet": doc[:200] + "..." if len(doc) > 200 else doc
                    }
                else:
                    # Keep the highest relevance score for this candidate
                    if relevance_score > candidates_map[file_name]["relevance_score"]:
                        candidates_map[file_name]["relevance_score"] = relevance_score
                        candidates_map[file_name]["resume_snippet"] = doc[:200] + "..." if len(doc) > 200 else doc
            
            # Convert to list and sort by relevance
            candidates = list(candidates_map.values())
            candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            # Convert to CandidateResult models
            candidate_results = [CandidateResult(**c) for c in candidates[:k]]
            
            self.logger.info(f"Retrieved {len(candidate_results)} candidates for query: {query}")
            return candidate_results
            
        except Exception as e:
            self.logger.error(f"Error in retrieval pipeline: {str(e)}")
            raise Exception(f"Failed to search resumes: {str(e)}")
    
    async def get_all_candidates(self) -> List[CandidateResult]:
        """Get all unique candidates from the database.
        
        Returns:
            List of all candidates with their metadata
        """
        try:
            # Get all metadata from vector store
            all_metadata = self.vector_store.get_all_metadata()
            
            # Group by file_name to get unique candidates
            candidates_map = {}
            
            for metadata in all_metadata:
                file_name = metadata.get("file_name")
                if file_name and file_name not in candidates_map:
                    candidates_map[file_name] = {
                        "candidate_name": metadata.get("candidate_name"),
                        "file_name": file_name,
                        "skills": metadata.get("skills", []),
                        "years_experience": metadata.get("years_experience"),
                        "relevance_score": 1.0,  # All candidates equally relevant for list-all
                        "resume_snippet": None
                    }
            
            # Convert to list sorted by candidate name
            candidates = list(candidates_map.values())
            candidates.sort(key=lambda x: x["candidate_name"] or x["file_name"])
            
            # Convert to CandidateResult models
            candidate_results = [CandidateResult(**c) for c in candidates]
            
            self.logger.info(f"Retrieved all {len(candidate_results)} candidates from database")
            return candidate_results
            
        except Exception as e:
            self.logger.error(f"Error getting all candidates: {str(e)}")
            raise Exception(f"Failed to get all candidates: {str(e)}")
    
    async def get_resume_by_filename(self, file_name: str) -> Optional[str]:
        """Retrieve full resume text by filename.
        
        Args:
            file_name: Name of the resume file
            
        Returns:
            Resume text if found, None otherwise
        """
        try:
            # Search with filename filter
            results = await self.vector_store.search(
                query="",  # Empty query to get all chunks
                top_k=100,  # Get many chunks
                filter_metadata={"file_name": file_name}
            )
            
            if not results["documents"]:
                return None
            
            # Combine all chunks for this resume
            full_text = "\n\n".join(results["documents"])
            return full_text
            
        except Exception as e:
            self.logger.error(f"Error retrieving resume by filename: {str(e)}")
            return None
    
    async def get_resume_by_candidate_name(self, candidate_name: str) -> Optional[tuple[str, str]]:
        """Retrieve full resume text by candidate name.
        
        Args:
            candidate_name: Name of the candidate (will search case-insensitive)
            
        Returns:
            Tuple of (file_name, resume_text) if found, None otherwise
        """
        try:
            # First, get all candidates to find the file name
            all_candidates = await self.get_all_candidates()
            
            # Search for matching candidate (case-insensitive)
            matching_candidate = None
            for candidate in all_candidates:
                if candidate.candidate_name and candidate_name.lower() in candidate.candidate_name.lower():
                    matching_candidate = candidate
                    break
            
            if not matching_candidate:
                return None
            
            # Now get the full resume by filename
            resume_text = await self.get_resume_by_filename(matching_candidate.file_name)
            if not resume_text:
                return None
            
            return (matching_candidate.file_name, resume_text)
            
        except Exception as e:
            self.logger.error(f"Error retrieving resume by candidate name: {str(e)}")
            return None
