"""Adapters for html_frontend to call existing backend modules and return JSON-serialisable primitives."""

from .documents import list_documents, get_document
from .stats import get_stats

__all__ = ["list_documents", "get_document", "get_stats"]
