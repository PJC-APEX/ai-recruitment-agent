"""Resume parser service using PyPDF."""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from pypdf import PdfReader
import re

logger = logging.getLogger(__name__)


class ResumeParserService:
    """Service for parsing resume PDF files."""
    
    def __init__(self, llm_client=None):
        """Initialize resume parser service.
        
        Args:
            llm_client: Optional LLM client for intelligent extraction
        """
        self.logger = logger
        self.llm_client = llm_client
    
    async def parse_pdf(self, file_path: str) -> str:
        """Parse PDF file and extract text content.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text content
            
        Raises:
            Exception: If parsing fails
        """
        return await asyncio.to_thread(self.parse_pdf_sync, file_path)

    def parse_pdf_sync(self, file_path: str) -> str:
        """Synchronous parser implementation executed in a worker thread."""
        try:
            reader = PdfReader(file_path)
            text_content = []

            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if text:
                    text_content.append(text)
                    self.logger.debug(f"Extracted text from page {page_num}")

            full_text = "\n\n".join(text_content)
            cleaned_text = self._clean_text(full_text)

            self.logger.info(f"Successfully parsed PDF: {file_path}")
            return cleaned_text

        except Exception as e:
            self.logger.error(f"Error parsing PDF {file_path}: {str(e)}")
            raise Exception(f"Failed to parse PDF: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing extra whitespace and special characters.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove multiple newlines
        text = re.sub(r'\n+', '\n', text)
        # Strip leading/trailing whitespace
        text = text.strip()
        return text
    
    def extract_email(self, text: str) -> Optional[str]:
        """Extract email address from text.
        
        Args:
            text: Resume text
            
        Returns:
            Email address if found, None otherwise
        """
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None
    
    def extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text.
        
        Args:
            text: Resume text
            
        Returns:
            Phone number if found, None otherwise
        """
        phone_pattern = r'(\+\d{1,3}[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}'
        match = re.search(phone_pattern, text)
        return match.group(0) if match else None
    
    async def extract_metadata_with_llm(self, resume_text: str) -> Dict[str, Any]:
        """Extract structured metadata from resume using LLM.
        
        Args:
            resume_text: Full text of the resume
            
        Returns:
            Dictionary with skills and years_experience
        """
        if not self.llm_client:
            self.logger.warning("LLM client not available, returning empty metadata")
            return {"skills": [], "years_experience": None, "_extraction_succeeded": False}
        
        try:
            from app.llm.prompt_templates import RESUME_EXTRACTION_PROMPT
            
            prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text)
            
            schema = {
                "skills": "list of strings",
                "years_experience": "integer or null"
            }
            
            metadata = await self.llm_client.generate_structured_output(
                prompt=prompt,
                schema=schema,
                system_message="You are an expert resume parser. Extract information accurately and comprehensively."
            )
            
            # Ensure skills is a list and filter out empty values
            skills = metadata.get("skills", [])
            if isinstance(skills, list):
                skills = [s.strip() for s in skills if s and s.strip()]
            else:
                skills = []
            
            # Ensure years_experience is an integer or None
            years_exp = metadata.get("years_experience")
            if years_exp is not None:
                try:
                    years_exp = int(years_exp)
                except (ValueError, TypeError):
                    years_exp = None
            
            self.logger.info(f"Extracted {len(skills)} skills and {years_exp} years of experience")
            
            return {
                "skills": skills,
                "years_experience": years_exp,
                "_extraction_succeeded": True,
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata with LLM: {str(e)}")
            return {
                "skills": [],
                "years_experience": None,
                "_extraction_succeeded": False,
            }
