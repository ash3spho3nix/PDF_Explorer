from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAdapter(ABC):
    def __init__(self, db, iam_client=None):
        self.db = db
        self.iam = iam_client

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        pass