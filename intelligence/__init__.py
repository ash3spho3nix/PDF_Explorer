"""
Intelligent Analysis Module (IAM)
Optional extension for PDF Inventory CLI.

Provides similarity, clustering, confidence estimation, relationship graphs,
and actionable insights without modifying the existing pipeline.
"""

from .iam_processor import IAMProcessor
from .config import IAMConfig
from .models import (
    PDFMetadata,
    SimilarityPair,
    ClusterAssignment,
    ConfidenceScore,
    GraphEdge,
    Insight,
)

__all__ = [
    "IAMProcessor",
    "IAMConfig",
    "PDFMetadata",
    "SimilarityPair",
    "ClusterAssignment",
    "ConfidenceScore",
    "GraphEdge",
    "Insight",
]