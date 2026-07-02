import os
import time
from pathlib import Path
from typing import List, Optional, BinaryIO, Dict, Any
from .base import StorageProvider, DocumentInfo


class LocalFilesystemProvider(StorageProvider):
    def __init__(self, root_path: str):
        self.root = Path(root_path).resolve()
        self._identifier = f"local:{self.root}"

    def list_documents(self, folder_id: Optional[str] = None,
                       recursive: bool = True) -> List[DocumentInfo]:
        start_path = Path(folder_id) if folder_id else self.root
        if not start_path.is_absolute():
            start_path = self.root / start_path
        pattern = "**/*.pdf" if recursive else "*.pdf"
        docs = []
        for p in start_path.glob(pattern):
            if p.is_file():
                stat = p.stat()
                docs.append(DocumentInfo(
                    id=str(p),
                    name=p.name,
                    path=str(p.relative_to(self.root)),
                    size_bytes=stat.st_size,
                    modified_time=stat.st_mtime,
                    metadata={"full_path": str(p)},
                    is_folder=False
                ))
        return docs

    def get_document(self, doc_id: str) -> Optional[DocumentInfo]:
        p = Path(doc_id)
        if not p.exists() or not p.is_file():
            return None
        stat = p.stat()
        return DocumentInfo(
            id=str(p),
            name=p.name,
            path=str(p.relative_to(self.root) if p.is_relative_to(self.root) else p),
            size_bytes=stat.st_size,
            modified_time=stat.st_mtime,
            metadata={"full_path": str(p)},
            is_folder=False
        )

    def get_metadata(self, doc_id: str) -> Dict[str, Any]:
        p = Path(doc_id)
        if not p.exists():
            return {}
        stat = p.stat()
        return {
            "full_path": str(p),
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime
        }

    def open_stream(self, doc_id: str) -> BinaryIO:
        return open(doc_id, "rb")

    def exists(self, doc_id: str) -> bool:
        return Path(doc_id).exists()

    def get_identifier(self) -> str:
        return self._identifier

    def get_modified_time(self, doc_id: str) -> float:
        return Path(doc_id).stat().st_mtime

    def get_size(self, doc_id: str) -> int:
        return Path(doc_id).stat().st_size