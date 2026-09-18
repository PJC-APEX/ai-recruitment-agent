"""SQLite-backed long-term memory metadata service."""
import sqlite3
import re
import asyncio
import threading
import chromadb
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self, db_path: str, embedding_service=None, collection_name: str = "user_memories"):
        path = Path(db_path)
        if not path.is_absolute(): path = Path.cwd() / path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(path)
        self.embedding_service = embedding_service
        self.vector_client = chromadb.PersistentClient(path=str(path.parent / "memory_chroma"))
        self.collection = self.vector_client.get_or_create_collection(name=collection_name)
        self._write_lock = threading.Lock()
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA busy_timeout = 10000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self):
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
                content TEXT NOT NULL, memory_type TEXT NOT NULL DEFAULT 'fact',
                importance REAL NOT NULL DEFAULT 0.5, confidence REAL NOT NULL DEFAULT 1.0,
                source_session_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                expires_at TEXT, is_deleted INTEGER NOT NULL DEFAULT 0)""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id, is_deleted)")

    @staticmethod
    def _now(): return datetime.now(timezone.utc).isoformat()
    @staticmethod
    def _to_dict(row):
        result = dict(row); result["is_deleted"] = bool(result["is_deleted"]); return result

    @staticmethod
    def _tokens(text: str) -> set[str]:
        """Create a lightweight mixed Chinese/English token set for fallback search."""
        return set(re.findall(r"[A-Za-z0-9_+#.-]+|[\u4e00-\u9fff]", text.lower()))

    async def _ensure_user_vectors(self, memories: list[dict]) -> None:
        """Backfill vectors for SQLite memories created before a vector write failed."""
        if not self.embedding_service or not memories:
            return
        ids = [str(memory["id"]) for memory in memories]
        existing_result = await asyncio.to_thread(self.collection.get, ids=ids)
        existing = set(existing_result.get("ids", []))
        missing = [memory for memory in memories if str(memory["id"]) not in existing]
        if not missing:
            return
        embeddings = await self.embedding_service.embed_documents([memory["content"] for memory in missing])
        await asyncio.to_thread(
            self.collection.upsert,
            ids=[str(memory["id"]) for memory in missing],
            documents=[memory["content"] for memory in missing],
            embeddings=embeddings,
            metadatas=[{"user_id": memory["user_id"], "memory_type": memory["memory_type"]} for memory in missing],
        )
        logger.info("[MemoryService] Backfilled %d missing memory vectors", len(missing))

    def create(self, *, user_id: str, content: str, memory_type: str = "fact", importance: float = 0.5,
               confidence: float = 1.0, source_session_id: Optional[str] = None,
               expires_at: Optional[datetime] = None) -> dict:
        now = self._now()
        with self._write_lock:
            with self._connect() as conn:
                cursor = conn.execute("""INSERT INTO memories
                    (user_id, content, memory_type, importance, confidence, source_session_id,
                     created_at, updated_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (user_id, content, memory_type, importance, confidence, source_session_id,
                     now, now, expires_at.isoformat() if expires_at else None))
                row = conn.execute("SELECT * FROM memories WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._to_dict(row)

    async def create_async(self, **kwargs) -> dict:
        return await asyncio.to_thread(self.create, **kwargs)

    def list_for_user(self, user_id: str):
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM memories WHERE user_id = ? AND is_deleted = 0 ORDER BY importance DESC, updated_at DESC", (user_id,)).fetchall()
        return [self._to_dict(row) for row in rows]

    async def list_for_user_async(self, user_id: str):
        return await asyncio.to_thread(self.list_for_user, user_id)

    async def retrieve_relevant(self, user_id: str, query: str, top_k: int = 5) -> list[dict]:
        """Return user memories ranked by simple token overlap and importance."""
        memories = await self.list_for_user_async(user_id)
        logger.info("[MemoryService] Found %d active memories for user %s", len(memories), user_id)
        if self.embedding_service:
            try:
                await self._ensure_user_vectors(memories)
                embedding = await self.embedding_service.embed_text(query)
                result = await asyncio.to_thread(
                    self.collection.query,
                    query_embeddings=[embedding],
                    n_results=top_k,
                    where={"user_id": user_id},
                )
                by_id = {str(m["id"]): m for m in memories}
                semantic = [by_id[i] for i in result.get("ids", [[]])[0] if i in by_id]
                if semantic:
                    logger.info("[MemoryService] Vector retrieval returned %d memories", len(semantic))
                    return semantic
                logger.info("[MemoryService] Vector retrieval returned no usable memories; using text fallback")
            except Exception as exc:
                logger.warning("[MemoryService] Vector retrieval failed; using text fallback: %s", exc)
        tokens = self._tokens(query)
        #回退机制
        scored = []
        for memory in memories:
            memory_tokens = self._tokens(memory["content"])
            overlap = len(tokens & memory_tokens)
            score = overlap + float(memory["importance"]) * 0.1
            if overlap > 0:
                scored.append((score, memory))
        scored.sort(key=lambda item: item[0], reverse=True)
        matches = [memory for _, memory in scored[:top_k]]
        logger.info("[MemoryService] Text fallback returned %d memories", len(matches))
        return matches

    def delete(self, memory_id: int, user_id: str) -> bool:
        with self._write_lock:
            with self._connect() as conn:
                cursor = conn.execute("UPDATE memories SET is_deleted = 1, updated_at = ? WHERE id = ? AND user_id = ? AND is_deleted = 0", (self._now(), memory_id, user_id))
        deleted = cursor.rowcount > 0
        if deleted:
            try: self.collection.delete(ids=[str(memory_id)])
            except Exception: pass
        return deleted

    async def _delete_vector_async(self, memory_id: int) -> None:
        await asyncio.to_thread(self.collection.delete, ids=[str(memory_id)])

    async def delete_async(self, memory_id: int, user_id: str) -> bool:
        # Avoid asyncio.run from a running request loop by keeping the SQL
        # mutation in a worker thread and deleting the vector asynchronously.
        deleted = await asyncio.to_thread(self._delete_sql, memory_id, user_id)
        if deleted:
            try:
                await self._delete_vector_async(memory_id)
            except Exception:
                logger.warning("Failed to delete vector for memory %s", memory_id, exc_info=True)
        return deleted

    def _delete_sql(self, memory_id: int, user_id: str) -> bool:
        with self._write_lock:
            with self._connect() as conn:
                cursor = conn.execute("UPDATE memories SET is_deleted = 1, updated_at = ? WHERE id = ? AND user_id = ? AND is_deleted = 0", (self._now(), memory_id, user_id))
        return cursor.rowcount > 0

    async def create_with_vector(self, **kwargs) -> dict:
        memory = await self.create_async(**kwargs)
        logger.info("[MemoryService] Saved memory %s to SQLite for user %s", memory["id"], memory["user_id"])
        if self.embedding_service:
            try:
                embedding = await self.embedding_service.embed_text(memory["content"])
                await asyncio.to_thread(
                    self.collection.upsert,
                    ids=[str(memory["id"])],
                    documents=[memory["content"]],
                    embeddings=[embedding],
                    metadatas=[{"user_id": memory["user_id"], "memory_type": memory["memory_type"]}],
                )
                logger.info("[MemoryService] Saved vector for memory %s", memory["id"])
            except Exception as exc:
                logger.warning("[MemoryService] SQLite save succeeded but vector save failed for memory %s: %s", memory["id"], exc)
        return memory

    async def save_extracted(self, *, user_id: str, content: str, memory_type: str,
                             importance: float, confidence: float,
                             source_session_id: Optional[str] = None) -> dict:
        memories = await self.list_for_user_async(user_id)
        tokens = self._tokens(content)
        for item in memories:
            old = self._tokens(item["content"])
            if tokens and len(tokens & old) / len(tokens | old) >= 0.8:
                logger.info("[MemoryService] Skipped duplicate memory for user %s (existing id %s)", user_id, item["id"])
                return item
        return await self.create_with_vector(user_id=user_id, content=content, memory_type=memory_type, importance=importance, confidence=confidence, source_session_id=source_session_id)
