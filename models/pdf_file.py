from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import json

if TYPE_CHECKING:
    from typing import Any as DocumentInfo


class PDFFlags:
    DUPLICATE = "duplicate"
    GENERIC_NAME = "generic_name"
    UNKNOWN = "unknown"
    ENCRYPTED = "encrypted"
    CORRUPTED = "corrupted"
    NEW = "new"


@dataclass
class PDFFile:
    path: str
    filename: str
    parent_folder: str

    size_bytes: int

    created_time: float
    modified_time: float

    hash: Optional[str]

    page_count: Optional[int]

    title: Optional[str]
    author: Optional[str]
    subject: Optional[str]
    keywords: Optional[str]

    category: str = "Unknown"
    subcategory: Optional[str] = None
    confidence: float = 0.0

    flags: List[str] = field(default_factory=list)
    classification_explanation: Optional[Dict[str, Any]] = None

    def to_flags_json(self) -> Optional[str]:
        """Serializes the flags list into a JSON-formatted string for SQLite storage."""
        if not self.flags:
            return None
        return json.dumps(self.flags)

    @classmethod
    def from_flags_json(cls, json_str: Optional[str]) -> List[str]:
        """Deserializes a JSON-formatted string from SQLite into a list of flag strings."""
        if not json_str:
            return []
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return []

    @classmethod
    def from_document_info(cls, info: "DocumentInfo") -> "PDFFile":
        """Construct a PDFFile from a legacy DocumentInfo structure."""
        return cls(
            path=getattr(info, "path", ""),
            filename=getattr(info, "filename", getattr(info, "name", "")),
            parent_folder=getattr(info, "parent_folder", str(Path(getattr(info, "path", "")).parent)),
            size_bytes=getattr(info, "size_bytes", 0),
            created_time=getattr(info, "created_time", 0.0),
            modified_time=getattr(info, "modified_time", 0.0),
            hash=getattr(info, "hash", None),
            page_count=getattr(info, "page_count", None),
            title=getattr(info, "title", None),
            author=getattr(info, "author", None),
            subject=getattr(info, "subject", None),
            keywords=getattr(info, "keywords", None),
            category=getattr(info, "category", "Unknown") or "Unknown",
            subcategory=getattr(info, "subcategory", None),
            confidence=getattr(info, "confidence", 0.0) or 0.0,
            flags=getattr(info, "flags", []) or [],
            classification_explanation=getattr(info, "classification_explanation", None)
        )

    @classmethod
    def from_pdf_metadata(cls, metadata: Dict[str, Any], path: str, filename: str, parent_folder: str) -> "PDFFile":
        """Construct a PDFFile from metadata dictionary values."""
        return cls(
            path=path,
            filename=filename,
            parent_folder=parent_folder,
            size_bytes=metadata.get("size_bytes", 0),
            created_time=metadata.get("created_time", 0.0),
            modified_time=metadata.get("modified_time", 0.0),
            hash=metadata.get("file_hash"),
            page_count=metadata.get("page_count", None),
            title=metadata.get("title", None),
            author=metadata.get("author", None),
            subject=metadata.get("subject", None),
            keywords=metadata.get("keywords", None),
            category=metadata.get("category", "Unknown") or "Unknown",
            subcategory=metadata.get("subcategory", None),
            confidence=metadata.get("confidence", 0.0) or 0.0,
            flags=metadata.get("flags", []) or [],
            classification_explanation=metadata.get("classification_explanation", None)
        )
