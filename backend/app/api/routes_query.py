"""API routes for querying and searching resumes."""

import logging
from fastapi import APIRouter, HTTPException, Depends
from app.dependencies import (
    get_retrieval_pipeline,
    get_ranking_service,
    get_llm_client,
    get_recruitment_agent
)
from app.rag.retrieval_pipeline import RetrievalPipeline
from app.services.ranking_service import RankingService
from app.llm.llm_client import LLMClient
from app.agents.recruitment_agent import RecruitmentAgent
from app.models.request_models import SearchRequest, ChatRequest, RankCandidatesRequest
from app.models.response_models import SearchResponse, ChatResponse, RankingResponse, RankedCandidate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/search-resumes", response_model=SearchResponse)
async def search_resumes(
    request: SearchRequest,
    retrieval_pipeline: RetrievalPipeline = Depends(get_retrieval_pipeline)
):
    """Search for resumes matching a natural language query.
    
    Args:
        request: Search request with query and optional top_k
        retrieval_pipeline: Retrieval pipeline
        
    Returns:
        Search results with matching candidates
    """
    try:
        logger.info(f"Searching resumes with query: {request.query}")
        
        # Perform retrieval
        results = await retrieval_pipeline.search_resumes(
            query=request.query,
            top_k=request.top_k
        )
        
        return SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results)
        )
        
    except Exception as e:
        logger.error(f"Error searching resumes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/rank-candidates", response_model=RankingResponse)
async def rank_candidates(
    request: RankCandidatesRequest,
    retrieval_pipeline: RetrievalPipeline = Depends(get_retrieval_pipeline),
    ranking_service: RankingService = Depends(get_ranking_service)
):
    """Rank candidates based on job description.
    
    Args:
        request: Ranking request with job description
        retrieval_pipeline: Retrieval pipeline
        ranking_service: Ranking service
        
    Returns:
        Ranked candidates with scores
    """
    try:
        logger.info("Ranking candidates for job description")
        
        # First, retrieve relevant candidates
        search_query = request.query or request.job_description
        candidates_results = await retrieval_pipeline.search_resumes(
            query=search_query,
            top_k=request.top_k
        )
        
        if not candidates_results:
            return RankingResponse(
                job_description=request.job_description,
                ranked_candidates=[],
                total_evaluated=0
            )
        
        # Get full resume text for each candidate
        candidates_data = []
        for candidate in candidates_results:
            resume_text = await retrieval_pipeline.get_resume_by_filename(
                candidate.file_name
            )
            if resume_text:
                candidates_data.append({
                    "candidate_name": candidate.candidate_name,
                    "file_name": candidate.file_name,
                    "resume_text": resume_text
                })
        
        # Rank candidates using LLM
        ranked_results = await ranking_service.rank_candidates(
            candidates=candidates_data,
            job_description=request.job_description
        )
        
        # Convert to response model
        ranked_candidates = [RankedCandidate(**r) for r in ranked_results]
        
        return RankingResponse(
            job_description=request.job_description,
            ranked_candidates=ranked_candidates,
            total_evaluated=len(ranked_candidates)
        )
        
    except Exception as e:
        logger.error(f"Error ranking candidates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ranking failed: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: RecruitmentAgent = Depends(get_recruitment_agent)
):
    """Chat endpoint using AI Agent for autonomous decision-making.
    
    This endpoint uses LangChain Agents to:
    1. Autonomously understand user intent
    2. Decide which tool(s) to call (search, list_all, get_details)
    3. Execute tools to gather accurate data from database
    4. Generate natural language responses with context
    
    Benefits over keyword matching:
    - No hardcoded keywords - AI understands natural language
    - More accurate - uses real database data instead of guessing
    - Extensible - easy to add new tools without modifying this endpoint
    - Follows SOLID principles - agent orchestration separate from business logic
    
    Args:
        request: Chat request with message and optional history
        agent: Injected RecruitmentAgent instance
        
    Returns:
        Chat response with AI-generated reply and optional candidate data
    """
    try:
        logger.info(f"Processing chat with AI Agent: {request.message}")
        
        # Convert chat history to LangChain format
        chat_history = []
        if request.chat_history:
            for msg in request.chat_history:
                role = msg.get("role")
                content = msg.get("content")
                if role == "user":
                    chat_history.append(("human", content))
                elif role == "assistant":
                    chat_history.append(("ai", content))
        
        # Let the agent autonomously decide what to do and execute
        result = await agent.process_query(
            query=request.message,
            chat_history=chat_history,
            session_id=request.session_id
        )
        
        if not result.get("success"):
            # Agent encountered an error
            logger.error(f"Agent error: {result.get('error')}")
            return ChatResponse(
                message=request.message,
                response=result.get("response", "I encountered an error processing your request."),
                data=None
            )
        
        # Agent succeeded - return response
        response_text = result.get("response", "")
        tools_used = result.get("tools_used", [])
        
        logger.info(f"Agent completed. Tools used: {tools_used}")
        
        return ChatResponse(
            message=request.message,
            response=response_text,
            data={"agent_tools_used": tools_used} if tools_used else None
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
