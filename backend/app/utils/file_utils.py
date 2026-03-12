"""Utility functions for file operations."""

import os
import hashlib
from typing import Optional
from pathlib import Path


def ensure_directory_exists(directory: str) -> None:
    """Create directory if it doesn't exist."""
    Path(directory).mkdir(parents=True, exist_ok=True)


def get_file_hash(file_path: str) -> str:
    """Generate MD5 hash of file content."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    return os.path.splitext(filename)[1].lower().lstrip(".")


def is_allowed_file(filename: str, allowed_extensions: list) -> bool:
    """Check if file extension is allowed."""
    return get_file_extension(filename) in allowed_extensions


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing unsafe characters."""
    # Remove any path components
    filename = os.path.basename(filename)
    # Replace unsafe characters
    unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    return filename


def get_file_size(file_path: str) -> int:
    """Get file size in bytes."""
    return os.path.getsize(file_path)


def extract_candidate_name_from_filename(filename: str) -> Optional[str]:
    """Extract candidate name from resume filename.
    
    Assumes filename format like: John_Doe_Resume.pdf
    """
    name_part = os.path.splitext(filename)[0]
    # Remove common resume keywords
    keywords = ['resume', 'cv', 'curriculum_vitae', '_resume', '_cv']
    for keyword in keywords:
        name_part = name_part.replace(keyword, '').replace(keyword.upper(), '')
    # Replace underscores and hyphens with spaces
    name_part = name_part.replace('_', ' ').replace('-', ' ')
    # Clean up extra spaces
    name_part = ' '.join(name_part.split()).strip()
    return name_part if name_part else None
