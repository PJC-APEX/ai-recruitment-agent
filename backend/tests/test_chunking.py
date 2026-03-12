"""Tests for chunking service."""

import pytest
from app.services.chunking_service import ChunkingService


@pytest.fixture
def chunking_service():
    """Create chunking service fixture."""
    return ChunkingService(chunk_size=100, chunk_overlap=20)


@pytest.mark.asyncio
async def test_chunk_text(chunking_service):
    """Test text chunking."""
    text = "A" * 250  # 250 character text
    
    chunks = await chunking_service.chunk_text(text)
    
    assert len(chunks) > 1  # Should create multiple chunks
    assert all(len(chunk) <= 120 for chunk in chunks)  # Respect chunk size + overlap


@pytest.mark.asyncio
async def test_chunk_short_text(chunking_service):
    """Test chunking text shorter than chunk size."""
    text = "Short text"
    
    chunks = await chunking_service.chunk_text(text)
    
    assert len(chunks) == 1
    assert chunks[0] == text


def test_get_chunk_info(chunking_service):
    """Test chunk configuration info."""
    info = chunking_service.get_chunk_info()
    
    assert info["chunk_size"] == 100
    assert info["chunk_overlap"] == 20
