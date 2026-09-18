"""Resumable resume ingestion pipeline used by ARQ and local fallback mode."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import Settings
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.resume_parser import ResumeParserService
from app.services.vector_store_service import VectorStoreService
from app.utils.file_utils import extract_candidate_name_from_filename

logger = logging.getLogger(__name__)
_local_locks: dict[str, asyncio.Lock] = {}
_local_locks_guard = asyncio.Lock()


async def local_ingestion_lock(file_hash: str) -> asyncio.Lock:
    """Return a per-file lock for the Redis-disabled single-process fallback."""
    async with _local_locks_guard:
        lock = _local_locks.get(file_hash)
        if lock is None:
            lock = asyncio.Lock()
            _local_locks[file_hash] = lock
        return lock


async def release_local_ingestion_lock(file_hash: str, lock: asyncio.Lock) -> None:
    async with _local_locks_guard:
        if _local_locks.get(file_hash) is lock and not lock.locked():
            _local_locks.pop(file_hash, None)


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(value, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_chunk_ids(file_hash: str, count: int) -> list[str]:
    """Build stable IDs so retries upsert rather than duplicate vectors."""
    return [f"{file_hash}:{index}" for index in range(count)]


async def _job_update(store, job_id: str, **fields: Any) -> None:
    if store is not None:
        await store.update(job_id, **fields)


async def process_resume_ingestion(
    *,
    job_id: str,
    file_path: str,
    file_hash: str,
    safe_filename: str,
    settings: Settings,
    resume_parser: ResumeParserService,
    chunking_service: ChunkingService,
    vector_store: VectorStoreService,
    store=None,
) -> Dict[str, Any]:
    """Run each ingestion stage and persist artifacts before advancing.

    A worker crash can therefore resume from ``parsed``, ``metadata``,
    ``chunked`` or ``embedded`` rather than reparsing and re-embedding the
    entire document.  Chroma IDs are deterministic and written with upsert.
    """
    artifact_dir = Path(settings.ingestion_artifact_directory) / job_id
    text_path = artifact_dir / "resume.txt"
    metadata_path = artifact_dir / "metadata.json"
    chunks_path = artifact_dir / "chunks.json"
    embeddings_path = artifact_dir / "embeddings.json"
    candidate_name = extract_candidate_name_from_filename(safe_filename)

    current = await store.get(job_id) if store is not None else {}
    stage = str(current.get("stage", "queued"))
    await _job_update(store, job_id, status="processing", stage=stage, error="")

    try:
        if not text_path.exists():
            await _job_update(store, job_id, status="processing", stage="parsing")
            resume_text = await resume_parser.parse_pdf(file_path)
            if not resume_text or len(resume_text) < 50:
                raise ValueError("Could not extract meaningful text from PDF")
            await asyncio.to_thread(_write_text, text_path, resume_text)
            stage = "parsed"
            await _job_update(store, job_id, status="processing", stage=stage)
        else:
            resume_text = await asyncio.to_thread(_read_text, text_path)

        metadata = None
        if metadata_path.exists():
            try:
                cached_metadata = await asyncio.to_thread(_read_json, metadata_path)
                if cached_metadata.get("_extraction_succeeded") is True:
                    metadata = cached_metadata
            except (OSError, ValueError, json.JSONDecodeError):
                metadata = None

        if metadata is None:
            await _job_update(store, job_id, status="processing", stage="metadata")
            extracted_metadata = await resume_parser.extract_metadata_with_llm(resume_text)
            if extracted_metadata.get("_extraction_succeeded") is not True:
                raise RuntimeError(
                    "Resume metadata extraction failed; retry after the LLM endpoint is available"
                )
            metadata = {
                "skills": extracted_metadata.get("skills") or [],
                "years_experience": extracted_metadata.get("years_experience"),
                "_extraction_succeeded": True,
            }
            await asyncio.to_thread(_write_json, metadata_path, metadata)
            stage = "metadata_extracted"
            await _job_update(store, job_id, status="processing", stage=stage, metadata=metadata)

        if not chunks_path.exists():
            await _job_update(store, job_id, status="processing", stage="chunking")
            chunks = await chunking_service.chunk_text(resume_text)
            if not chunks:
                raise ValueError("No text chunks were created from the resume")
            await asyncio.to_thread(_write_json, chunks_path, chunks)
            stage = "chunked"
            await _job_update(store, job_id, status="processing", stage=stage, chunks_created=len(chunks))
        else:
            chunks = await asyncio.to_thread(_read_json, chunks_path)

        ids = _build_chunk_ids(file_hash, len(chunks))
        metadatas = []
        for index in range(len(chunks)):
            item = {
                "file_name": safe_filename,
                "candidate_name": candidate_name,
                "chunk_index": index,
                "total_chunks": len(chunks),
                "resume_id": file_hash,
            }
            if metadata.get("skills"):
                item["skills"] = metadata["skills"]
            if metadata.get("years_experience") is not None:
                item["years_experience"] = metadata["years_experience"]
            metadatas.append(item)

        # Embeddings are checkpointed batch by batch.  If a worker is killed
        # halfway through this stage, the next attempt only processes the
        # missing suffix rather than starting from PDF parsing again.
        embeddings = []
        if embeddings_path.exists():
            try:
                embeddings = await asyncio.to_thread(_read_json, embeddings_path)
                if not isinstance(embeddings, list):
                    embeddings = []
            except (OSError, ValueError, json.JSONDecodeError):
                embeddings = []
        if len(embeddings) > len(chunks):
            embeddings = []
        if len(embeddings) < len(chunks):
            await _job_update(store, job_id, status="processing", stage="embedding")
            batch_size = max(1, int(getattr(settings, "ingestion_embedding_batch_size", 16)))
            for start in range(len(embeddings), len(chunks), batch_size):
                batch = await vector_store.embedding_service.embed_documents(
                    chunks[start:start + batch_size]
                )
                embeddings.extend(batch)
                await asyncio.to_thread(_write_json, embeddings_path, embeddings)
            stage = "embedded"
            await _job_update(store, job_id, status="processing", stage=stage)

        if stage == "embedded" or stage != "indexed":
            await _job_update(store, job_id, status="processing", stage="indexing")
            vector_lock = None
            if store is not None:
                vector_lock = await store.acquire_lock(
                    "global-vector-store-write",
                    getattr(settings, "ingestion_lock_ttl_seconds", 1800),
                )
                if not vector_lock:
                    raise RuntimeError("Vector store is busy; retry ingestion later")
            try:
                await vector_store.upsert_documents(
                    texts=chunks,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings,
                )
            finally:
                if store is not None and vector_lock:
                    await store.release_lock("global-vector-store-write", vector_lock)
            stage = "indexed"

        result = {
            "success": True,
            "status": "indexed",
            "stage": "indexed",
            "job_id": job_id,
            "file_name": safe_filename,
            "chunks_created": len(chunks),
            "metadata": {
                "candidate_name": candidate_name,
                "skills": metadata.get("skills") or [],
                "years_experience": metadata.get("years_experience"),
                "file_name": safe_filename,
            },
        }
        await _job_update(store, job_id, status="indexed", stage="indexed", result=result)
        return result
    except Exception as exc:
        logger.exception("Resume ingestion failed for job %s", job_id)
        await _job_update(store, job_id, status="failed", error=str(exc))
        raise
