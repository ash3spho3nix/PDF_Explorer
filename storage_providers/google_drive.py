import io
import time
import logging
from typing import List, Optional, BinaryIO, Dict, Any
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from .base import StorageProvider, DocumentInfo
from .oauth import OAuth2Manager
from .cache import CacheManager

logger = logging.getLogger(__name__)


class GoogleDriveProvider(StorageProvider):
    def __init__(self, account: str, client_id: str, client_secret: str,
                 token_dir: str, cache_dir: str,
                 folder_id: Optional[str] = None,
                 shared_drive_id: Optional[str] = None,
                 shared_with_me: bool = False,
                 max_cache_size_gb: float = 10.0):
        self.account = account
        self.folder_id = folder_id or "root"
        self.shared_drive_id = shared_drive_id
        self.shared_with_me = shared_with_me
        self.oauth = OAuth2Manager(client_id, client_secret, token_dir, account)
        self.service = build("drive", "v3", credentials=self.oauth.get_credentials())
        self.cache = CacheManager(cache_dir, max_size_gb=max_cache_size_gb)
        self._identifier = f"gdrive:{account}:{self.folder_id}"

    def _get_creds(self):
        return self.oauth.get_credentials()

    def _refresh_service(self):
        self.service = build("drive", "v3", credentials=self._get_creds())

    def list_documents(self, folder_id: Optional[str] = None,
                       recursive: bool = True) -> List[DocumentInfo]:
        self._refresh_service()
        query_parts = []
        if self.shared_with_me:
            query_parts.append("sharedWithMe=true")
        else:
            parent = folder_id or self.folder_id
            query_parts.append(f"'{parent}' in parents")
        query_parts.append("mimeType='application/pdf'")
        query_parts.append("trashed=false")
        query = " and ".join(query_parts)

        fields = "files(id,name,size,modifiedTime,parents,mimeType,webViewLink)"
        params = {
            "q": query,
            "fields": f"nextPageToken, {fields}",
            "pageSize": 1000,
        }
        if self.shared_drive_id:
            params["driveId"] = self.shared_drive_id
            params["corpora"] = "drive"

        docs = []
        page_token = None
        while True:
            if page_token:
                params["pageToken"] = page_token
            results = self.service.files().list(**params).execute()
            for f in results.get("files", []):
                docs.append(DocumentInfo(
                    id=f["id"],
                    name=f["name"],
                    path=f.get("name", ""),
                    size_bytes=int(f.get("size", 0)),
                    modified_time=time.mktime(time.strptime(
                        f["modifiedTime"], "%Y-%m-%dT%H:%M:%S.%fZ"
                    )),
                    metadata=f,
                    is_folder=False
                ))
            page_token = results.get("nextPageToken")
            if not page_token:
                break
        return docs

    def get_document(self, doc_id: str) -> Optional[DocumentInfo]:
        self._refresh_service()
        try:
            f = self.service.files().get(fileId=doc_id, fields="*").execute()
            return DocumentInfo(
                id=f["id"],
                name=f["name"],
                path=f.get("name", ""),
                size_bytes=int(f.get("size", 0)),
                modified_time=time.mktime(time.strptime(
                    f["modifiedTime"], "%Y-%m-%dT%H:%M:%S.%fZ"
                )),
                metadata=f,
                is_folder=False
            )
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None

    def get_metadata(self, doc_id: str) -> Dict[str, Any]:
        self._refresh_service()
        try:
            f = self.service.files().get(fileId=doc_id, fields="*").execute()
            return f
        except Exception as e:
            logger.error(f"Failed to get metadata for {doc_id}: {e}")
            return {}

    def open_stream(self, doc_id: str) -> BinaryIO:
        self._refresh_service()
        # Check cache first
        cached_path = self.cache.get(doc_id)
        if cached_path and Path(cached_path).exists():
            return open(cached_path, "rb")

        # Download to cache
        request = self.service.files().get_media(fileId=doc_id)
        file_handle = io.BytesIO()
        downloader = MediaIoBaseDownload(file_handle, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        file_handle.seek(0)
        # Save to cache
        self.cache.put(doc_id, file_handle)
        file_handle.seek(0)
        return file_handle

    def exists(self, doc_id: str) -> bool:
        self._refresh_service()
        try:
            self.service.files().get(fileId=doc_id, fields="id").execute()
            return True
        except Exception:
            return False

    def get_identifier(self) -> str:
        return self._identifier

    def get_modified_time(self, doc_id: str) -> float:
        meta = self.get_metadata(doc_id)
        if "modifiedTime" in meta:
            return time.mktime(time.strptime(
                meta["modifiedTime"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ))
        return 0.0

    def get_size(self, doc_id: str) -> int:
        meta = self.get_metadata(doc_id)
        return int(meta.get("size", 0))

    def download_if_needed(self, doc_id: str, local_path: str) -> None:
        if not Path(local_path).exists():
            with self.open_stream(doc_id) as stream:
                with open(local_path, "wb") as f:
                    f.write(stream.read())

    def get_change_token(self) -> Optional[str]:
        self._refresh_service()
        try:
            result = self.service.changes().getStartPageToken().execute()
            return result.get("startPageToken")
        except Exception:
            return None