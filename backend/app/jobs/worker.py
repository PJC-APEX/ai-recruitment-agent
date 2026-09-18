"""ARQ worker entrypoint for resume ingestion.

Run from ``backend`` with:

    python -m arq app.jobs.worker.WorkerSettings
"""

from __future__ import annotations

import logging
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.config import get_settings
from app.jobs.ingestion_queue import IngestionJobStore, _redis_settings
from app.jobs.resume_ingestion import process_resume_ingestion
from app.llm.llm_client import LLMClient
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.resume_parser import ResumeParserService
from app.services.vector_store_service import VectorStoreService

try:  # pragma: no cover - imported only by an ARQ worker process
    from arq.connections import RedisSettings
except ImportError:  # pragma: no cover
    RedisSettings = None

logger = logging.getLogger(__name__)


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is not None:
        return value
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            key, separator, raw = line.partition("=")
            if separator and key.strip() == name:
                return raw.strip().strip('"').strip("'")
    return default


async def ingest_resume(ctx, job_id: str):
    """Process one logical job, resuming from its last durable stage."""
    settings = ctx["settings"]
    store = IngestionJobStore(
        ctx["redis"],
        ttl_seconds=settings.ingestion_job_ttl_seconds,
    )
    job = await store.get(job_id)
    if not job:
        raise ValueError(f"Ingestion job does not exist: {job_id}")
    if job.get("status") == "indexed":
        return job.get("result") or job

    # Older queued jobs may predate the explicit field; their logical job_id
    # is already the SHA-256 file hash, so safely fall back to it.
    file_hash = str(job.get("file_hash") or job_id)
    lock_token = await store.acquire_lock(file_hash, settings.ingestion_lock_ttl_seconds)
    if not lock_token:
        # Another worker owns this logical file.  Returning successfully lets
        # ARQ discard this duplicate attempt; the owner will finish the job.
        logger.info("Skipping duplicate ingestion attempt for %s", job_id)
        return await store.get(job_id)

    async def refresh_lock() -> None:
        interval = max(10, settings.ingestion_lock_ttl_seconds // 3)
        while True:
            await asyncio.sleep(interval)
            if not await store.refresh_lock(file_hash, lock_token, settings.ingestion_lock_ttl_seconds):
                logger.warning("Lost ingestion lock for %s", job_id)
                return

    lock_refresh_task = asyncio.create_task(refresh_lock())
    try:
        return await process_resume_ingestion(
            job_id=job_id,
            file_path=str(job["file_path"]),
            file_hash=file_hash,
            safe_filename=str(job["file_name"]),
            settings=settings,
            resume_parser=ctx["resume_parser"],
            chunking_service=ctx["chunking_service"],
            vector_store=ctx["vector_store"],
            store=store,
        )
    finally:
        lock_refresh_task.cancel()
        try:
            await lock_refresh_task
        except asyncio.CancelledError:
            pass
        await store.release_lock(file_hash, lock_token)


async def startup(ctx):
    settings = get_settings()
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL is required for the ARQ worker")
    llm_client = LLMClient(
        api_key=settings.azure_openai_api_key,
        endpoint=settings.azure_openai_endpoint,
        model=settings.azure_openai_model,
        api_version=settings.azure_openai_api_version,
    )
    embedding = EmbeddingService(
        api_key=settings.embedding_api_key or settings.azure_openai_api_key,
        endpoint=settings.embedding_base_url or settings.azure_openai_endpoint,
        model=settings.azure_openai_embedding_model,
        api_version=settings.azure_openai_api_version,
        max_concurrency=settings.ingestion_embedding_concurrency,
        timeout_seconds=settings.embedding_timeout_seconds,
        max_retries=settings.embedding_max_retries,
        retry_min_seconds=settings.embedding_retry_min_seconds,
        retry_max_seconds=settings.embedding_retry_max_seconds,
    )
    ctx["settings"] = settings
    asyncio.get_running_loop().set_default_executor(
        ThreadPoolExecutor(max_workers=max(1, settings.sync_thread_pool_workers))
    )
    ctx["resume_parser"] = ResumeParserService(llm_client=llm_client)
    ctx["chunking_service"] = ChunkingService(settings.chunk_size, settings.chunk_overlap)
    ctx["vector_store"] = VectorStoreService(settings.chroma_persist_directory, embedding)


class WorkerSettings:
    functions = [ingest_resume]
    on_startup = startup
    # Must match the queue name used by the API's enqueue_job call.
    queue_name = "resume-ingestion"
    max_jobs = max(1, int(_env("INGESTION_WORKER_MAX_JOBS", "4")))
    keep_result = 3600
    retry_jobs = True
    _configured_redis_url = _env("REDIS_URL")
    if _configured_redis_url:
        redis_settings = _redis_settings(_configured_redis_url)
    elif RedisSettings is not None:
        # Keep module importable for documentation/tests; starting the worker
        # without REDIS_URL still fails with a clear startup error.
        redis_settings = RedisSettings()
