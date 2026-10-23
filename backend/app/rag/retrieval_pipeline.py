"""RAG retrieval pipeline for searching resumes."""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from app.services.vector_store_service import VectorStoreService
from app.models.response_models import CandidateResult
from app.utils.file_utils import extract_candidate_name_from_text

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
                candidate_name = extract_candidate_name_from_text(doc) or metadata.get("candidate_name")
                
                # Calculate relevance score (1 - normalized distance)
                # ChromaDB uses cosine distance, so lower is better
                relevance_score = 1.0 - (distance / 2.0)  # Normalize to 0-1
                
                if file_name not in candidates_map:
                    candidates_map[file_name] = {
                        "candidate_name": candidate_name,
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
                        if candidate_name:
                            candidates_map[file_name]["candidate_name"] = candidate_name
            
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
            # Start with metadata only. For identity resolution, fetch one
            # representative chunk per file rather than loading every resume
            # chunk into memory just to render the candidate list.
            all_metadata = await self.vector_store.get_all_metadata_async()
            documents_by_file: Dict[str, str] = {}
            if hasattr(self.vector_store, "get_by_metadata_async"):
                file_names = sorted(
                    {
                        str(metadata.get("file_name"))
                        for metadata in all_metadata
                        if metadata.get("file_name")
                    }
                )

                async def load_first_chunk(file_name: str):
                    records = await self.vector_store.get_by_metadata_async(
                        filter_metadata={"file_name": file_name},
                        limit=1,
                    )
                    documents = records.get("documents") or []
                    return file_name, documents[0] if documents else ""

                loaded = await asyncio.gather(
                    *(load_first_chunk(file_name) for file_name in file_names)
                )
                documents_by_file = dict(loaded)
            
            # Group by file_name to get unique candidates
            candidates_map = {}
            
            for metadata in all_metadata:
                file_name = metadata.get("file_name")
                if file_name and file_name not in candidates_map:
                    document = documents_by_file.get(file_name, "")
                    candidates_map[file_name] = {
                        "candidate_name": extract_candidate_name_from_text(document) or metadata.get("candidate_name"),
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
            # File-name lookup is an exact metadata query. It must not call
            # the embedding service with an empty query string.
            results = await self.vector_store.get_by_metadata_async(
                filter_metadata={"file_name": file_name},
                limit=100,
            )
            
            if not results["documents"]:
                return None
            
            # Combine chunks in source order and remove exact duplicate chunks.
            # Older ingestion runs used non-deterministic IDs and can leave
            # identical copies behind; those must not multiply the prompt.
            records = list(zip(results["documents"], results.get("metadatas") or []))
            records.sort(key=lambda item: int(item[1].get("chunk_index", 0)))
            seen_documents: set[str] = set()
            unique_documents = []
            for document, _metadata in records:
                if document in seen_documents:
                    continue
                seen_documents.add(document)
                unique_documents.append(document)
            full_text = "\n\n".join(unique_documents)
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
            
            query = self._normalize_candidate_identifier(candidate_name)
            if not query:
                return None

            # Prefer an exact canonical name or filename match. Only allow a
            # partial match when it is unique; never silently choose the first
            # similarly named candidate.
            exact = [
                candidate
                for candidate in all_candidates
                if query in {
                    self._normalize_candidate_identifier(candidate.candidate_name),
                    self._normalize_candidate_identifier(candidate.file_name),
                }
            ]
            matches = exact or [
                candidate
                for candidate in all_candidates
                if candidate.candidate_name
                and (
                    query in self._normalize_candidate_identifier(candidate.candidate_name)
                    or self._normalize_candidate_identifier(candidate.candidate_name) in query
                )
            ]
            if len(matches) != 1:
                if len(matches) > 1:
                    self.logger.warning(
                        "Ambiguous candidate name '%s' matched %d candidates",
                        candidate_name,
                        len(matches),
                    )
                return None

            matching_candidate = matches[0]
            
            # Now get the full resume by filename
            resume_text = await self.get_resume_by_filename(matching_candidate.file_name)
            if not resume_text:
                return None
            
            return (matching_candidate.file_name, resume_text)
            
        except Exception as e:
            self.logger.error(f"Error retrieving resume by candidate name: {str(e)}")
            return None

    @staticmethod
    def _normalize_candidate_identifier(value: Optional[str]) -> str:
        """Normalize names and filenames for deterministic identity matching."""
        import re

        normalized = str(value or "").strip().lower()
        normalized = re.sub(r"\.(?:pdf|docx?)$", "", normalized)
        normalized = normalized.replace("简历", "").replace("resume", "")
        normalized = re.sub(r"[\s_\-]+", "", normalized)
        return normalized
