"""Initialize API package."""

from app.api import (
    routes_feishu,
    routes_resume,
    routes_query,
    routes_scoring,
    routes_memory,
)

__all__ = [
    "routes_feishu",
    "routes_resume",
    "routes_query",
    "routes_scoring",
    "routes_memory",
]
