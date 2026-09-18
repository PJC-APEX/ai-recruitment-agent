"""API endpoints for long-term memory management."""
from fastapi import APIRouter, Depends, HTTPException, Query
from app.dependencies import get_memory_service
from app.models.memory_models import MemoryCreateRequest, MemoryResponse
from app.services.memory_service import MemoryService

router = APIRouter()

@router.post("/memories", response_model=MemoryResponse)
async def create_memory(request: MemoryCreateRequest, service: MemoryService = Depends(get_memory_service)):
    return await service.create_with_vector(**request.model_dump())

@router.get("/memories", response_model=list[MemoryResponse])
async def list_memories(user_id: str = Query(...), service: MemoryService = Depends(get_memory_service)):
    return await service.list_for_user_async(user_id)

@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: int, user_id: str = Query(...), service: MemoryService = Depends(get_memory_service)):
    if not await service.delete_async(memory_id, user_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True, "memory_id": memory_id}
