"""API routes for resume upload and management."""

import logging
import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.dependencies import (
    get_resume_parser_service,
    get_chunking_service,
    get_vector_store_service,
    get_settings
)
from app.services.resume_parser import ResumeParserService
from app.services.chunking_service import ChunkingService
from app.services.vector_store_service import VectorStoreService
from app.config import Settings
from app.models.response_models import ResumeUploadResponse, ResumeMetadata
from app.utils.file_utils import (
    ensure_directory_exists,
    sanitize_filename,
    extract_candidate_name_from_filename
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload-resume", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    resume_parser: ResumeParserService = Depends(get_resume_parser_service),
    chunking_service: ChunkingService = Depends(get_chunking_service),
    vector_store: VectorStoreService = Depends(get_vector_store_service),
    settings: Settings = Depends(get_settings)
):
    """Upload and process a resume PDF file.
    
    Args:
        file: PDF file upload
        resume_parser: Resume parser service
        chunking_service: Chunking service
        vector_store: Vector store service
        settings: Application settings
        
    Returns:
        Upload response with metadata
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Sanitize filename
        original_filename = file.filename
        safe_filename = sanitize_filename(original_filename)
        
        # Create data directory if it doesn't exist
        data_dir = "data/resumes"
        ensure_directory_exists(data_dir)
        
        # Save uploaded file temporarily
        file_path = os.path.join(data_dir, safe_filename)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"Saved uploaded file: {safe_filename}")
        
        # Parse PDF
        resume_text = await resume_parser.parse_pdf(file_path)
        
        if not resume_text or len(resume_text) < 50:
            raise HTTPException(status_code=400, detail="Could not extract meaningful text from PDF")
        
        # Extract candidate name from filename
        candidate_name = extract_candidate_name_from_filename(safe_filename)
        
        # Extract skills and years of experience using LLM
        logger.info("Extracting metadata using LLM...")
        extracted_metadata = await resume_parser.extract_metadata_with_llm(resume_text)
        skills = extracted_metadata.get("skills", [])
        years_experience = extracted_metadata.get("years_experience")
        
        logger.info(f"Extracted {len(skills)} skills and {years_experience} years of experience")
        
        # Chunk the resume text
        chunks = await chunking_service.chunk_text(resume_text)
        
        # Prepare metadata and IDs for each chunk
        chunk_ids = []
        chunk_metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{safe_filename}_{uuid.uuid4().hex[:8]}_{i}"
            chunk_ids.append(chunk_id)
            
            metadata = {
                "file_name": safe_filename,
                "candidate_name": candidate_name,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            
            # Add skills only if the list is not empty (ChromaDB doesn't allow empty lists)
            if skills and len(skills) > 0:
                metadata["skills"] = skills
            
            # Add years_experience only if it has a value
            if years_experience is not None:
                metadata["years_experience"] = years_experience
            
            chunk_metadatas.append(metadata)
        
        # Add to vector store
        await vector_store.add_documents(
            texts=chunks,
            metadatas=chunk_metadatas,
            ids=chunk_ids
        )
        
        logger.info(f"Successfully indexed resume: {safe_filename}")
        
        # Prepare response with extracted metadata
        resume_metadata = ResumeMetadata(
            candidate_name=candidate_name,
            skills=skills if skills else [],
            years_experience=years_experience,
            file_name=safe_filename
        )
        
        return ResumeUploadResponse(
            success=True,
            message=f"Resume uploaded and indexed successfully",
            file_name=safe_filename,
            chunks_created=len(chunks),
            metadata=resume_metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading resume: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload resume: {str(e)}")


@router.get("/resumes/count")
async def get_resume_count(
    vector_store: VectorStoreService = Depends(get_vector_store_service)
):
    """Get the total count of indexed resume chunks.
    
    Returns:
        Total count of documents in vector store
    """
    try:
        count = vector_store.get_collection_count()
        return {"total_documents": count}
    except Exception as e:
        logger.error(f"Error getting resume count: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resumes/list")
async def list_resumes(
    vector_store: VectorStoreService = Depends(get_vector_store_service)
):
    """List all unique resumes in the system.
    
    Returns:
        List of unique resume filenames with metadata
    """
    try:
        all_metadata = vector_store.get_all_metadata()
        
        # Group by filename to get unique resumes
        unique_resumes = {}
        for metadata in all_metadata:
            file_name = metadata.get("file_name")
            if file_name and file_name not in unique_resumes:
                unique_resumes[file_name] = {
                    "file_name": file_name,
                    "candidate_name": metadata.get("candidate_name")
                }
        
        return {
            "resumes": list(unique_resumes.values()),
            "total_resumes": len(unique_resumes)
        }
        
    except Exception as e:
        logger.error(f"Error listing resumes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
