import os
import shutil
from pathlib import Path
from typing import Optional, BinaryIO
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    def __init__(self, cache_dir: str, max_size_gb: float = 10.0):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = int(max_size_gb * 1024**3)

    def get(self, doc_id: str) -> Optional[Path]:
        candidate = self.cache_dir / doc_id
        if candidate.exists():
            return candidate
        return None

    def put(self, doc_id: str, stream: BinaryIO) -> Path:
        target = self.cache_dir / doc_id
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            stream.seek(0)
            shutil.copyfileobj(stream, f)
        self._evict_if_needed()
        return target

    def clear(self):
        shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _evict_if_needed(self):
        total = sum(f.stat().st_size for f in self.cache_dir.glob("*") if f.is_file())
        if total > self.max_size_bytes:
            # Simple LRU: delete oldest accessed files
            files = [(f, f.stat().st_atime) for f in self.cache_dir.glob("*") if f.is_file()]
            files.sort(key=lambda x: x[1])
            for f, _ in files:
                if total <= self.max_size_bytes * 0.8:
                    break
                size = f.stat().st_size
                f.unlink()
                total -= size
                logger.info(f"Evicted {f} from cache")