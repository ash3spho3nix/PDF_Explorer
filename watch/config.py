from pydantic import BaseModel
from typing import List, Optional


class WatchConfig(BaseModel):
    directories: List[str]
    exclude_patterns: List[str] = []
    scan_interval: int = 300
    debounce_delay: float = 2.0
    state_dir: str = "./watch_state"
    cache_path: str = "pdf_inventory.db"
    log_file: Optional[str] = None