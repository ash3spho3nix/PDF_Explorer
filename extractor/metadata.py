"""
Extracts structural core property headers out of targeted document candidates.
"""

import pypdf
from typing import Dict, Any


class MetadataExtractor:
    """Queries underlying document catalogs utilizing safe header extraction calls."""

    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Reads document catalogs safely. Returns data dictionary.
        """
        result: Dict[str, Any] = {
            "page_count": 0,
            "title": None,
            "author": None,
            "subject": None,
            "keywords": None,
            "encrypted": False
        }

        try:
            # Keep stream processing tight. Avoid pulling the entire file structure into memory.
            with open(pdf_path, "rb") as stream:
                reader = pypdf.PdfReader(stream)
                
                result["page_count"] = len(reader.pages)
                
                if reader.is_encrypted:
                    result["encrypted"] = True
                    return result
                
                info = reader.metadata
                if info:
                    result["title"] = str(info.title) if info.title else None
                    result["author"] = str(info.author) if info.author else None
                    result["subject"] = str(info.subject) if info.subject else None
                    result["keywords"] = str(info.keywords) if info.keywords else None
                    
        except Exception:
            # Any extraction failure treats the object safely as non-readable or corrupted down-funnel.
            pass

        return result