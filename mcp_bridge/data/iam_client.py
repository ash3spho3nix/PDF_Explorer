"""Stub IAM client. Replace with real implementation when intelligence/ is integrated."""
from typing import Optional


class IAMClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    def search_similar(self, query: str, limit: int = 10):
        """Placeholder — returns empty until IAM is wired in."""
        return []
