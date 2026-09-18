"""ARQ/Redis helpers for durable, idempotent resume ingestion jobs.

Redis is deliberately imported lazily.  The API can still run in the local
quickstart without Redis; production deployments enable the queue through
``INGESTION_QUEUE_ENABLED=true``.
"""

from __future__ import annotations

import json
import asyncio
import time
import uuid
from typing import Any, Dict, Optional
from urllib.parse import urlparse


try:  # pragma: no cover - availability depends on deployment extras
    from arq import create_pool
    from arq.connections import RedisSettings
except ImportError:  # pragma: no cover
    create_pool = None
    RedisSettings = None


JOB_PREFIX = "resume-ingestion:job:"
LOCK_PREFIX = "resume-ingestion:lock:"
_pool = None
_pool_lock = asyncio.Lock()


def _redis_settings(redis_url: str):
    if create_pool is None or RedisSettings is None:
        raise RuntimeError("ARQ/Redis dependencies are not installed")
    parsed = urlparse(redis_url)
    if parsed.scheme not in {"redis", "rediss"}:
        raise ValueError("REDIS_URL must use redis:// or rediss://")
    database = int((parsed.path or "/0").lstrip("/") or 0)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=database,
        username=parsed.username,
        password=parsed.password,
        ssl=parsed.scheme == "rediss",
    )


async def create_arq_pool(redis_url: str):
    """Create an ARQ Redis pool from a normal Redis URL."""
    return await create_pool(_redis_settings(redis_url))


async def get_arq_pool(redis_url: str):
    """Lazily create one Redis/ARQ pool per API process."""
    global _pool
    if _pool is not None:
        return _pool
    async with _pool_lock:
        if _pool is None:
            _pool = await create_arq_pool(redis_url)
    return _pool


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


class IngestionJobStore:
    """Small Redis-backed job state repository.

    A job's logical ID is derived from the uploaded file hash.  The hash makes
    duplicate uploads converge on one job, while the ARQ task ID can change on
    retry.  Stage fields are updated after each durable artifact is written so
    a restarted worker resumes at the last completed stage.
    """

    def __init__(self, redis, *, ttl_seconds: int = 86400):
        self.redis = redis
        self.ttl_seconds = max(60, int(ttl_seconds))

    @staticmethod
    def key(job_id: str) -> str:
        return f"{JOB_PREFIX}{job_id}"

    async def create_or_get(self, job_id: str, **fields: Any) -> tuple[Dict[str, Any], bool]:
        key = self.key(job_id)
        created = await self.redis.hsetnx(key, "job_id", job_id)
        if created:
            payload = {
                "job_id": job_id,
                "status": "queued",
                "stage": "queued",
                "created_at": str(time.time()),
                "updated_at": str(time.time()),
                **fields,
            }
            await self.redis.hset(key, mapping={k: self._encode(v) for k, v in payload.items()})
            await self.redis.expire(key, self.ttl_seconds)
            return payload, True
        # hsetnx is intentionally used as the creation gate.  A concurrent
        # duplicate may observe the gate before the creator has written the
        # remaining fields, so wait briefly for the canonical record.
        for _ in range(20):
            existing = await self.get(job_id)
            if existing.get("file_path") or existing.get("status") == "indexed":
                return existing, False
            await asyncio.sleep(0.01)
        existing = await self.get(job_id)
        if not existing.get("file_path"):
            # The original creator may have died between the hsetnx gate and
            # its field write.  Complete that orphaned record so enqueueing it
            # cannot create a job without a source file.
            payload = {
                "job_id": job_id,
                "status": "queued",
                "stage": "queued",
                "created_at": str(time.time()),
                "updated_at": str(time.time()),
                **fields,
            }
            await self.redis.hset(key, mapping={k: self._encode(v) for k, v in payload.items()})
            await self.redis.expire(key, self.ttl_seconds)
            return payload, True
        return existing, False

    async def get(self, job_id: str) -> Dict[str, Any]:
        raw = await self.redis.hgetall(self.key(job_id))
        result: Dict[str, Any] = {}
        for key, value in raw.items():
            if isinstance(key, bytes):
                key = key.decode()
            result[str(key)] = self._decode(value)
        return result

    async def update(self, job_id: str, **fields: Any) -> Dict[str, Any]:
        payload = {"updated_at": str(time.time()), **fields}
        await self.redis.hset(self.key(job_id), mapping={k: self._encode(v) for k, v in payload.items()})
        await self.redis.expire(self.key(job_id), self.ttl_seconds)
        return await self.get(job_id)

    async def enqueue(self, job_id: str, *, queue_name: str = "resume-ingestion") -> bool:
        """Enqueue a retry-safe task if the logical job is not complete."""
        job = await self.get(job_id)
        if not job:
            raise KeyError(f"Unknown ingestion job: {job_id}")
        if job.get("status") == "indexed":
            return False

        # A unique attempt ID prevents a stale ARQ result key from blocking a
        # resumed logical job.  Redis state and deterministic vector IDs still
        # provide the actual idempotency guarantee.
        task_id = f"{job_id}:attempt:{uuid.uuid4().hex}"
        await self.update(job_id, status="queued", stage=job.get("stage") or "queued")
        await self.redis.enqueue_job(
            "ingest_resume",
            job_id,
            _job_id=task_id,
            _queue_name=queue_name,
        )
        await self.update(job_id, enqueued_at=str(time.time()))
        return True

    async def acquire_lock(self, file_hash: str, ttl_seconds: int) -> Optional[str]:
        token = uuid.uuid4().hex
        acquired = await self.redis.set(
            f"{LOCK_PREFIX}{file_hash}", token, nx=True, ex=max(30, int(ttl_seconds))
        )
        return token if acquired else None

    async def release_lock(self, file_hash: str, token: str) -> None:
        key = f"{LOCK_PREFIX}{file_hash}"
        # Delete only our own lock.  This avoids releasing a lock acquired by a
        # newer worker after our TTL expired.
        script = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"
        await self.redis.eval(script, 1, key, token)

    async def refresh_lock(self, file_hash: str, token: str, ttl_seconds: int) -> bool:
        key = f"{LOCK_PREFIX}{file_hash}"
        script = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('expire', KEYS[1], ARGV[2]) else return 0 end"
        result = await self.redis.eval(script, 1, key, token, max(30, int(ttl_seconds)))
        return bool(result)

    @staticmethod
    def _encode(value: Any) -> str:
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    @staticmethod
    def _decode(value: Any) -> Any:
        if isinstance(value, bytes):
            value = value.decode()
        if not isinstance(value, str):
            return value
        if value.startswith("{") or value.startswith("["):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return value
