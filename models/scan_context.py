"""
Defines the execution context and state models for the PDF inventory scanning process.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from models.pdf_file import PDFFile


@dataclass
class ScanContext:
    """
    Global state object carrying configuration, resource handles, stats,
    and progress tracking throughout the scan pipeline execution loop.
    """
    root_path: str
    config: Dict[str, Any] = field(default_factory=dict)
    
    # SQLite connection proxy or direct handle
    sqlite_conn: Any = None
    
    # Execution metrics and run tracking
    stats: Dict[str, Any] = field(default_factory=lambda: {
        "total_pdfs": 0,
        "total_size_bytes": 0,
        "scanned_folders": 0,
        "processed_files": 0
    })
    cache: Dict[str, Any] = field(default_factory=dict)
    
    # UI hooks
    progress: Any = None  # rich.progress.Progress instance
    logger: Any = None    # Application logger instance
    
    start_time: float = 0.0


@dataclass
class FolderSummary:
    """Represents calculated structural metrics for an individual directory containing PDFs."""
    folder_path: str
    total_files: int
    total_size_bytes: int
    category_counts: Dict[str, int] = field(default_factory=dict)
    folder_score: float = 100.0


@dataclass
class ScanReport:
    """Final structural aggregate container used to feed the report generation engines."""
    run_id: str
    start_time: float
    end_time: float
    total_pdfs: int
    total_size_bytes: int
    pdfs: List[PDFFile] = field(default_factory=list)
    folder_summaries: Dict[str, FolderSummary] = field(default_factory=dict)
    global_category_breakdown: Dict[str, int] = field(default_factory=dict)
    findings: List[str] = field(default_factory=list)