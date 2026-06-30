from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import json


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

    category: str
    subcategory: Optional[str]
    confidence: float

    flags: List[str]
    classification_explanation: Optional[Dict[str, Any]] = None

    def to_flags_json(self) -> str:
        """Serializes the flags list into a JSON-formatted string for SQLite storage."""
        return json.dumps(self.flags)

    @classmethod
    def from_flags_json(cls, json_str: str) -> List[str]:
        """Deserializes a JSON-formatted string from SQLite into a list of flag strings."""
        if not json_str:
            return []
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return []