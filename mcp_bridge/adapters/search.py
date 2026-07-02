from .base import BaseAdapter
from typing import Dict, Any
class SearchAdapter(BaseAdapter):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query", "")
        limit = params.get("limit", 20)
        # Call existing search service (via IAM or SQL)
        results = self.data_access.search_documents(query, limit)
        # Format as MCP text content
        return {
            "content": [
                {"type": "text", "text": self._format_results(results)}
            ]
        }