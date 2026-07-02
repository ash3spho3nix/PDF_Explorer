# config.py
from typing import Optional
from pydantic_settings import BaseSettings

class BridgeConfig(BaseSettings):
    db_path: str = "pdf_inventory.db"
    iam_endpoint: Optional[str] = None
    log_level: str = "INFO"
    
    class Config:
        env_prefix = "PDF_BRIDGE_"