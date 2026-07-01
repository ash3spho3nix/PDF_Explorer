from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import json


class PDFMetadata(BaseModel):
    """Minimal metadata as passed from the existing pipeline."""
    id: int
    file_path: str
    file_hash: str
    filename: str
    title: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    keywords: List[str] = []
    year: Optional[int] = None
    page_count: Optional[int] = None
    category: Optional[str] = None
    folder: Optional[str] = None
    size_bytes: Optional[int] = None
    modified_time: Optional[datetime] = None
    created_time: Optional[datetime] = None


class SimilarityPair(BaseModel):
    pdf_id_1: int
    pdf_id_2: int
    strategy: str  # "deterministic", "embedding"
    score: float
    embedding_vector: Optional[bytes] = None  # for caching


class ClusterAssignment(BaseModel):
    pdf_id: int
    cluster_id: int  # -1 for noise
    algorithm: str
    parameters: Dict[str, Any]


class ConfidenceScore(BaseModel):
    pdf_id: int
    category: str
    confidence: int  # 0-100
    reasons: List[str]


class GraphEdge(BaseModel):
    source: int
    target: int
    edge_type: str  # "similarity", "same_author", "same_publisher", "same_topic", "same_keywords", "same_folder"
    weight: float


class Insight(BaseModel):
    type: str
    severity: str  # "info", "warning", "critical"
    title: str
    description: str
    affected_pdf_ids: List[int]
    extra_data: Optional[Dict[str, Any]] = None

    def to_markdown(self) -> str:
        return f"**{self.severity.upper()}** – {self.title}\n{self.description}\n"