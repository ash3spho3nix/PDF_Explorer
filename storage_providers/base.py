from abc import ABC, abstractmethod
from typing import List, Optional, BinaryIO, Dict, Any
from dataclasses import dataclass


@dataclass
class DocumentInfo:
    id: str
    name: str
    path: str
    size_bytes: int
    modified_time: float  # UTC timestamp
    metadata: Dict[str, Any]
    is_folder: bool = False


class StorageProvider(ABC):
    @abstractmethod
    def list_documents(self, folder_id: Optional[str] = None,
                       recursive: bool = True) -> List[DocumentInfo]:
        """List all PDF documents under the given folder."""
        pass

    @abstractmethod
    def get_document(self, doc_id: str) -> Optional[DocumentInfo]:
        """Retrieve document info by ID."""
        pass

    @abstractmethod
    def get_metadata(self, doc_id: str) -> Dict[str, Any]:
        """Return extended metadata for a document."""
        pass

    @abstractmethod
    def open_stream(self, doc_id: str) -> BinaryIO:
        """Open a readable binary stream for the document content."""
        pass

    @abstractmethod
    def exists(self, doc_id: str) -> bool:
        """Check if the document still exists."""
        pass

    @abstractmethod
    def get_identifier(self) -> str:
        """Return a unique string identifying this provider instance."""
        pass

    @abstractmethod
    def get_modified_time(self, doc_id: str) -> float:
        """Get last modification timestamp of the document."""
        pass

    @abstractmethod
    def get_size(self, doc_id: str) -> int:
        """Get file size in bytes."""
        pass

    def download_if_needed(self, doc_id: str, local_path: str) -> None:
        """Download the document to a local cache if not already present."""
        pass

    def get_change_token(self) -> Optional[str]:
        """Return a token for incremental sync (cloud providers)."""
        return None