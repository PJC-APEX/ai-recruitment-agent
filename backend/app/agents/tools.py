"""LangChain tools for recruitment agent.

This module defines tools following SOLID principles:
- Single Responsibility: Each tool does ONE thing
- Open/Closed: Easy to add new tools without modifying existing code
- Interface Segregation: Clean, focused tool interfaces
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_core.tools import Tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Tool Input Schemas (Following Interface Segregation Principle)
class SearchCandidatesInput(BaseModel):
    """Input schema for search_candidates tool."""
    query: str = Field(description="Natural language search query for finding candidates with specific skills or experience")


class GetCandidateDetailsInput(BaseModel):
    """Input schema for get_candidate_details tool."""
    identifier: str = Field(description="The candidate's file name (e.g., 'john_doe.pdf') OR candidate name (e.g., 'John Doe')")


# Tool Functions (Following Single Responsibility Principle)
def create_search_candidates_tool(retrieval_pipeline) -> Tool:
    """Create a tool for searching candidates by skills or criteria.
    
    Args:
        retrieval_pipeline: RetrievalPipeline instance
        
    Returns:
        LangChain Tool for searching candidates
    """
    async def search_candidates(query: str) -> str:
        """Search for candidates matching specific criteria.
        
        Args:
            query: Natural language search query
            
        Returns:
            Formatted string with candidate results
        """
        try:
            logger.info(f"Tool: Searching candidates with query: {query}")
            results = await retrieval_pipeline.search_resumes(query=query, top_k=5)
            
            if not results:
                return "No candidates found matching the search criteria."
            
            # Format results as a readable string
            output = f"Found {len(results)} matching candidates:\n\n"
            for i, candidate in enumerate(results, 1):
                name = candidate.candidate_name or "Unknown"
                score = f"{candidate.relevance_score:.1%}"
                skills = ", ".join(candidate.skills[:5]) if candidate.skills else "N/A"
                years = f"{candidate.years_experience} years" if candidate.years_experience else "N/A"
                
                output += f"{i}. {name} (File: {candidate.file_name})\n"
                output += f"   Relevance Score: {score}\n"
                output += f"   Experience: {years}\n"
                output += f"   Key Skills: {skills}\n"
                if candidate.resume_snippet:
                    output += f"   Snippet: {candidate.resume_snippet[:150]}...\n"
                output += "\n"
            
            return output
            
        except Exception as e:
            logger.error(f"Error in search_candidates tool: {str(e)}")
            return f"Error searching candidates: {str(e)}"
    
    return Tool(
        name="search_candidates",
        func=search_candidates,
        description="Search for candidates who match specific skills, experience, or requirements. Use this when the user wants to find candidates with particular qualifications like 'Python developers' or '5+ years experience'.",
        args_schema=SearchCandidatesInput,
        coroutine=search_candidates  # Mark as async
    )


def create_list_all_candidates_tool(retrieval_pipeline) -> Tool:
    """Create a tool for listing all candidates in the database.
    
    Args:
        retrieval_pipeline: RetrievalPipeline instance
        
    Returns:
        LangChain Tool for listing all candidates
    """
    async def list_all_candidates() -> str:
        """List all candidates in the database.
        
        Returns:
            Formatted string with all candidates
        """
        try:
            logger.info("Tool: Listing all candidates")
            results = await retrieval_pipeline.get_all_candidates()
            
            if not results:
                return "There are no candidates in the database yet."
            
            # Format results as a readable string emphasizing filenames
            output = f"Total candidates in database: {len(results)}\n\n"
            output += "IMPORTANT: When using get_candidate_details, use the EXACT filename shown below:\n\n"
            
            for i, candidate in enumerate(results, 1):
                name = candidate.candidate_name or "Unknown"
                skills = ", ".join(candidate.skills[:5]) if candidate.skills else "N/A"
                years = f"{candidate.years_experience} years" if candidate.years_experience else "N/A"
                
                # Put filename FIRST and make it prominent
                output += f"{i}. FILENAME: {candidate.file_name}\n"
                output += f"   Name: {name}\n"
                output += f"   Experience: {years}\n"
                output += f"   Key Skills: {skills}\n\n"
            
            return output
            
        except Exception as e:
            logger.error(f"Error in list_all_candidates tool: {str(e)}")
            return f"Error listing candidates: {str(e)}"
    
    return Tool(
        name="list_all_candidates",
        func=list_all_candidates,
        description="List ALL candidates in the resume database. Use this when the user asks 'how many candidates', 'list all', 'show everyone', or wants to see the complete list of candidates.",
        args_schema=None,  # No input parameters needed
        coroutine=list_all_candidates  # Mark as async
    )


def create_get_candidate_details_tool(retrieval_pipeline) -> Tool:
    """Create a tool for getting detailed information about a specific candidate.
    
    Args:
        retrieval_pipeline: RetrievalPipeline instance
        
    Returns:
        LangChain Tool for getting candidate details
    """
    async def get_candidate_details(identifier: str) -> str:
        """Get detailed resume information for a specific candidate.
        
        Args:
            identifier: The candidate's file name OR candidate name
            
        Returns:
            Detailed candidate information
        """
        try:
            logger.info(f"Tool: Getting details for: {identifier}")
            
            # First, try as filename
            resume_text = await retrieval_pipeline.get_resume_by_filename(identifier)
            file_name = identifier
            
            # If not found, try as candidate name
            if not resume_text:
                logger.info(f"Not found as filename, trying as candidate name...")
                result = await retrieval_pipeline.get_resume_by_candidate_name(identifier)
                if result:
                    file_name, resume_text = result
                    logger.info(f"Found candidate by name: {file_name}")
            
            if not resume_text:
                return f"Could not find resume for: {identifier}. Please check the candidate name or file name."
            
            # Truncate if too long
            if len(resume_text) > 2000:
                resume_text = resume_text[:2000] + "...\n[Resume truncated for brevity]"
            
            output = f"Full resume details for {file_name}:\n\n{resume_text}"
            return output
            
        except Exception as e:
            logger.error(f"Error in get_candidate_details tool: {str(e)}")
            return f"Error getting candidate details: {str(e)}"
    
    return Tool(
        name="get_candidate_details",
        func=get_candidate_details,
        description="Get detailed resume information for a specific candidate. IMPORTANT: Use the EXACT FILENAME from list_all_candidates output (copy the text after 'FILENAME: '). Example: 'SSE-SivaramakrishnanG-Connectrz.pdf' NOT 'Sivaramakrishnan G'. You can also try candidate names, but filenames are more reliable.",
        args_schema=GetCandidateDetailsInput,
        coroutine=get_candidate_details  # Mark as async
    )
