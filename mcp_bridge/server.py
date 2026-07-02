import asyncio
import json
import logging
from typing import Dict, Any

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

from .adapters import (
    SearchAdapter, CategoryAdapter, DocumentAdapter,
    DuplicateAdapter, SimilarityAdapter, FolderAdapter,
    StatsAdapter, WeeklyAdapter, FindingsAdapter,
    MetadataAdapter, ConfidenceAdapter,
)
from .data.db import ReadOnlySQLite
from .data.iam_client import IAMClient
from .config import BridgeConfig

logger = logging.getLogger(__name__)

_TOOLS = [
    {
        "name": "search_documents",
        "description": "Search PDFs by filename, title, author, or category.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_document",
        "description": "Get full metadata for a PDF by its absolute path.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "get_categories",
        "description": "Return hierarchical category breakdown (category > subcategory > count).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_duplicates",
        "description": "Return groups of duplicate PDFs (same file hash).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_folder_stats",
        "description": "Return per-folder stats: file count, total size, avg confidence.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_stats",
        "description": "Return overall index stats: total PDFs, size, confidence, category counts.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_recent",
        "description": "Return recently modified PDFs.",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 20}},
        },
    },
    {
        "name": "get_findings",
        "description": "Return actionable findings: low-confidence classifications, duplicates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "threshold": {"type": "number", "default": 0.4},
                "limit": {"type": "integer", "default": 50},
            },
        },
    },
    {
        "name": "get_similar",
        "description": "Return documents in the same category, ordered by confidence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["category"],
        },
    },
    {
        "name": "get_metadata",
        "description": "Return full stored metadata for a PDF path.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "get_confidence_distribution",
        "description": "Return confidence score distribution across the index.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

_ADAPTER_MAP = {
    "search_documents": SearchAdapter,
    "get_document": DocumentAdapter,
    "get_categories": CategoryAdapter,
    "get_duplicates": DuplicateAdapter,
    "get_folder_stats": FolderAdapter,
    "get_stats": StatsAdapter,
    "get_recent": WeeklyAdapter,
    "get_findings": FindingsAdapter,
    "get_similar": SimilarityAdapter,
    "get_metadata": MetadataAdapter,
    "get_confidence_distribution": ConfidenceAdapter,
}


class MCPBridgeServer:
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.db = ReadOnlySQLite(config.db_path)
        self.iam = IAMClient(config.iam_endpoint) if config.iam_endpoint else None
        self.server = Server("pdf-inventory-bridge")
        self._register_handlers()

    def _register_handlers(self):
        self.server.list_tools()(self._list_tools)
        self.server.call_tool()(self._call_tool)
        self.server.list_resources()(self._list_resources)
        self.server.read_resource()(self._read_resource)

    async def _list_tools(self):
        return _TOOLS

    async def _call_tool(self, name: str, arguments: Dict[str, Any]):
        adapter_class = _ADAPTER_MAP.get(name)
        if not adapter_class:
            raise ValueError(f"Unknown tool: {name}")
        result = await adapter_class(self.db, self.iam).execute(arguments)
        return result

    async def _list_resources(self):
        return []

    async def _read_resource(self, uri: str):
        raise NotImplementedError("No resources exposed.")

    async def run_stdio(self):
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="pdf-inventory-bridge",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


def main():
    config = BridgeConfig()
    server = MCPBridgeServer(config)
    asyncio.run(server.run_stdio())
