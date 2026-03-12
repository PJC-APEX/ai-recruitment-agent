"""Tests for resume parser service."""

import pytest
from app.services.resume_parser import ResumeParserService


@pytest.fixture
def parser_service():
    """Create parser service fixture."""
    return ResumeParserService()


def test_clean_text(parser_service):
    """Test text cleaning functionality."""
    raw_text = "This   has    extra    spaces\n\n\n\nAnd multiple newlines"
    cleaned = parser_service._clean_text(raw_text)
    
    assert "   " not in cleaned
    assert "\n\n\n" not in cleaned


def test_extract_email(parser_service):
    """Test email extraction."""
    text = "Contact me at john.doe@example.com for details"
    email = parser_service.extract_email(text)
    
    assert email == "john.doe@example.com"


def test_extract_email_not_found(parser_service):
    """Test email extraction when no email present."""
    text = "No email address here"
    email = parser_service.extract_email(text)
    
    assert email is None


def test_extract_phone(parser_service):
    """Test phone number extraction."""
    text = "Call me at 123-456-7890"
    phone = parser_service.extract_phone(text)
    
    assert phone is not None
    assert "123" in phone


# Add more tests for PDF parsing when you have test PDF files
@pytest.mark.asyncio
async def test_parse_pdf_file_not_found(parser_service):
    """Test PDF parsing with non-existent file."""
    with pytest.raises(Exception):
        await parser_service.parse_pdf("nonexistent.pdf")
