"""API routes for resume upload and management."""

import logging
import os
import uuid
import asyncio
import hashlib
from pathlib import Path
from typing import BinaryIO
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Response
from app.dependencies import (
    get_resume_parser_service,
    get_chunking_service,
    get_vector_store_service,
    get_settings
)
from app.services.vector_store_service import VectorStoreService
from app.config import Settings
from app.models.response_models import ResumeUploadResponse, ResumeMetadata
from app.utils.file_utils import sanitize_filename, extract_candidate_name_from_filename
from app.jobs.ingestion_queue import IngestionJobStore, get_arq_pool
from app.jobs.resume_ingestion import (
    local_ingestion_lock,
    process_resume_ingestion,
    release_local_ingestion_lock,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class UploadSizeExceeded(ValueError):
    """Raised when a streamed upload exceeds the configured byte limit."""


def _copy_upload_sync(source: BinaryIO, destination: str, max_size: int) -> tuple[str, int]:
    """Stream an upload to disk and calculate its hash in one thread."""
    digest = hashlib.sha256()
    total = 0
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("wb") as output:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_size:
                    raise UploadSizeExceeded(f"File exceeds the {max_size} byte upload limit")
                digest.update(chunk)
                output.write(chunk)
    except Exception:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return digest.hexdigest(), total


async def _persist_upload(file: UploadFile, settings: Settings) -> tuple[str, str, int]:
    data_dir = Path(settings.upload_data_directory)
    temp_path = data_dir / f".{uuid.uuid4().hex}.upload"
    file_hash, size = await asyncio.to_thread(
        _copy_upload_sync,
        file.file,
        str(temp_path),
        settings.max_upload_size,
    )
    canonical_path = data_dir / f"{file_hash}.pdf"
    if await asyncio.to_thread(canonical_path.exists):
        await asyncio.to_thread(temp_path.unlink, True)
    else:
        await asyncio.to_thread(os.replace, str(temp_path), str(canonical_path))
    return str(canonical_path.resolve()), file_hash, size


@router.post("/upload-resume", response_model=ResumeUploadResponse)
async def upload_resume(
    response: Response,
    file: UploadFile = File(...),
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
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        safe_filename = sanitize_filename(file.filename)
        file_path, file_hash, _ = await _persist_upload(file, settings)
        candidate_name = extract_candidate_name_from_filename(safe_filename)

        if settings.ingestion_queue_enabled:
            if not settings.redis_url:
                raise HTTPException(status_code=503, detail="Ingestion queue is enabled but REDIS_URL is missing")
            try:
                redis = await get_arq_pool(settings.redis_url)
            except Exception as exc:
                logger.error("Unable to connect to ingestion queue: %s", exc)
                raise HTTPException(status_code=503, detail="Ingestion queue is unavailable") from exc

            store = IngestionJobStore(redis, ttl_seconds=settings.ingestion_job_ttl_seconds)
            job, created = await store.create_or_get(
                file_hash,
                file_hash=file_hash,
                file_path=file_path,
                file_name=safe_filename,
            )
            effective_filename = str(job.get("file_name") or safe_filename)
            effective_candidate_name = extract_candidate_name_from_filename(effective_filename)
            status = str(job.get("status", "queued"))
            if status == "indexed" and isinstance(job.get("result"), dict):
                completed = job["result"]
                return ResumeUploadResponse(
                    success=True,
                    message="Resume was already indexed",
                    file_name=completed.get("file_name", effective_filename),
                    chunks_created=int(completed.get("chunks_created", 0) or 0),
                    metadata=ResumeMetadata(**completed.get("metadata", {
                        "candidate_name": effective_candidate_name,
                        "skills": [],
                        "years_experience": None,
                        "file_name": effective_filename,
                    })),
                    job_id=file_hash,
                    status="indexed",
                )
            should_enqueue = created or status == "failed" or (
                status == "queued" and not job.get("enqueued_at")
            )
            if should_enqueue:
                task_id = f"{file_hash}:attempt:{uuid.uuid4().hex}"
                await redis.enqueue_job(
                    "ingest_resume",
                    file_hash,
                    _job_id=task_id,
                    _queue_name=settings.ingestion_queue_name,
                )
                await store.update(
                    file_hash,
                    status="queued",
                    stage=job.get("stage", "queued"),
                    enqueued_at=str(asyncio.get_running_loop().time()),
                    error="",
                )
                # The old value can be "failed" when this is a retry. Return
                # the new state so the frontend polls the job instead of
                # incorrectly showing the synchronous "indexed" message.
                status = "queued"

            if response is not None:
                response.status_code = 202

            return ResumeUploadResponse(
                success=True,
                message="Resume accepted and queued for indexing",
                file_name=effective_filename,
                chunks_created=int(job.get("chunks_created", 0) or 0),
                metadata=ResumeMetadata(
                    candidate_name=effective_candidate_name,
                    skills=[],
                    years_experience=None,
                    file_name=effective_filename,
                ),
                job_id=file_hash,
                status=status,
            )

        # Local fallback retains the existing synchronous response contract.
        # PDF/Chunk/Chroma disk work is moved to worker threads by services.
        resume_parser = get_resume_parser_service()
        chunking_service = get_chunking_service()
        vector_store = get_vector_store_service()
        local_lock = await local_ingestion_lock(file_hash)
        try:
            async with local_lock:
                result = await process_resume_ingestion(
                    job_id=file_hash,
                    file_path=file_path,
                    file_hash=file_hash,
                    safe_filename=safe_filename,
                    settings=settings,
                    resume_parser=resume_parser,
                    chunking_service=chunking_service,
                    vector_store=vector_store,
                )
        finally:
            await release_local_ingestion_lock(file_hash, local_lock)
        return ResumeUploadResponse(
            success=True,
            message="Resume uploaded and indexed successfully",
            file_name=safe_filename,
            chunks_created=result["chunks_created"],
            metadata=ResumeMetadata(**result["metadata"]),
            job_id=file_hash,
            status="indexed",
        )
        
    except HTTPException:
        raise
    except UploadSizeExceeded as e:
        raise HTTPException(status_code=413, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error uploading resume: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload resume: {str(e)}")


@router.get("/upload-jobs/{job_id}")
async def get_upload_job(
    job_id: str,
    settings: Settings = Depends(get_settings),
):
    """Return queued resume ingestion status and the completed result."""
    if not settings.ingestion_queue_enabled or not settings.redis_url:
        raise HTTPException(status_code=404, detail="Ingestion queue is not enabled")
    try:
        redis = await get_arq_pool(settings.redis_url)
        job = await IngestionJobStore(
            redis,
            ttl_seconds=settings.ingestion_job_ttl_seconds,
        ).get(job_id)
    except Exception as exc:
        logger.error("Unable to read ingestion job %s: %s", job_id, exc)
        raise HTTPException(status_code=503, detail="Ingestion queue is unavailable") from exc
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return job


@router.get("/resumes/count")
async def get_resume_count(
    vector_store: VectorStoreService = Depends(get_vector_store_service)
):
    """Get the total count of indexed resume chunks.
    
    Returns:
        Total count of documents in vector store
    """
    try:
        count = await vector_store.get_collection_count_async()
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
        all_metadata = await vector_store.get_all_metadata_async()
        
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
