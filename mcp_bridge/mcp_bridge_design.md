# MCP Bridge Design

## Overview
The MCP Bridge is an independent module that exposes the PDF Inventory system's capabilities through the Model Context Protocol (MCP). It acts as a read‑only wrapper around existing services—Scanner, Extractor, Classifier, SQLite Cache, and the Intelligent Analysis Module (IAM)—without modifying their internals. The bridge translates MCP requests into calls to the underlying services and returns structured responses that can be consumed by any MCP‑compatible client (Claude Desktop, VS Code, Cursor, OpenAI‑compatible clients, etc.).

---

## 1. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP Hosts                             │
│  (Claude Desktop, VS Code, Cursor, OpenAI-compatible, …)   │
└────────────────────────┬────────────────────────────────────┘
                         │ MCP Protocol (JSON‑RPC over stdio/HTTP)
┌────────────────────────▼────────────────────────────────────┐
│                      MCP Bridge                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  MCP Server (FastMCP / custom)                       │ │
│  │  - Handles JSON‑RPC messages                         │ │
│  │  - Exposes Tools, Resources, Prompts                 │ │
│  └──────────────────┬─────────────────────────────────────┘ │
│                     │                                       │
│  ┌──────────────────▼─────────────────────────────────────┐ │
│  │  Capability Adapters                                 │ │
│  │  - SearchAdapter      - StatsAdapter                │ │
│  │  - CategoryAdapter    - WeeklyAdapter               │ │
│  │  - DocumentAdapter    - FindingsAdapter             │ │
│  │  - DuplicateAdapter   - MetadataAdapter             │ │
│  │  - SimilarityAdapter  - ConfidenceAdapter           │ │
│  │  - FolderAdapter                                   │ │
│  └──────────────────┬─────────────────────────────────────┘ │
│                     │                                       │
│  ┌──────────────────▼─────────────────────────────────────┐ │
│  │  Data Access Layer (Read‑only)                       │ │
│  │  - SQLiteDB wrapper (queries only)                  │ │
│  │  - IAM client (for similarity)                      │ │
│  │  - CacheManager                                     │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│           Existing PDF Inventory Services                   │
│  Scanner → Extractor → Classifier → SQLite Cache → IAM     │
└─────────────────────────────────────────────────────────────┘
```

**Key components:**
- **MCP Server**: Implements the MCP protocol (using `mcp` library or custom). Handles tool calls, resource URIs, and prompt requests.
- **Capability Adapters**: Each adapter encapsulates one domain capability. They transform MCP parameters into service calls and format outputs as MCP content (text, JSON, etc.).
- **Data Access Layer**: Read‑only access to SQLite cache and IAM. No writes are performed.
- **Configuration**: Environment variables or config file for database path, IAM endpoint, logging, etc.

---

## 2. Package Layout

```
pdf_inventory/
├── mcp_bridge/
│   ├── __init__.py
│   ├── server.py                 # MCP server entry point
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py               # Abstract adapter class
│   │   ├── search.py
│   │   ├── category.py
│   │   ├── document.py
│   │   ├── duplicate.py
│   │   ├── similarity.py
│   │   ├── folder.py
│   │   ├── stats.py
│   │   ├── weekly.py
│   │   ├── findings.py
│   │   ├── metadata.py
│   │   └── confidence.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── db.py                 # SQLite read‑only wrapper
│   │   ├── iam_client.py         # IAM HTTP client (if separate)
│   │   └── cache.py              # CacheManager wrapper
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py           # Pydantic models for incoming params
│   │   └── responses.py          # MCP content models
│   ├── config.py                 # Configuration loading
│   └── utils/
│       ├── __init__.py
│       └── logging.py
└── tests/
    └── mcp_bridge/
        └── ...
```

---

## 3. Public Interfaces

---

## 4. Tool Definitions

MCP tools are functions that the host can invoke. Each tool corresponds to a capability. We define the tool name, description, input schema (JSON Schema), and output format.

| Tool Name | Description | Input Schema (example) | Output |
|-----------|-------------|------------------------|--------|
| `search_documents` | Full‑text search across PDF content and metadata | `{ "query": string, "limit": integer (default 20) }` | List of matching documents with metadata |
| `get_categories` | Retrieve hierarchical categories and counts | `{ "parent": string (optional) }` | Nested category tree with counts |
| `get_document` | Get detailed info for a single PDF by path or ID | `{ "path": string }` | Full PDFFile object (sanitized) |
| `find_duplicates` | List duplicate groups | `{ "min_group_size": integer (default 2) }` | Groups of duplicate file paths |
| `find_similar` | Find semantically similar documents (IAM) | `{ "path": string, "threshold": float (0.0‑1.0), "limit": integer }` | List of similar documents with similarity scores |
| `get_folder_summary` | Summary stats per folder | `{ "folder": string (optional) }` | Folder stats: file count, size, categories, score |
| `get_statistics` | Overall statistics | `{}` | Total count, size, category breakdown, etc. |
| `get_weekly_changes` | Changes since last scan | `{ "weeks_ago": integer (default 1) }` | New, modified, deleted files |
| `get_interesting_findings` | Generate interesting findings | `{}` | List of findings with descriptions |
| `get_metadata` | Retrieve metadata for a document | `{ "path": string }` | Title, author, subject, keywords, page count |
| `get_confidence` | Get classification confidence | `{ "path": string }` | Confidence score and debug info |

### Input Schemas (JSON Schema)
Each tool input schema will be published via MCP's `tools/list` endpoint. We'll define them using Pydantic models for validation.

### Output Format
All tools return MCP `TextContent` or `EmbeddedResource` content. For structured data (e.g., statistics), we can return JSON text that the client can parse.

---

## 5. Resource Definitions

MCP resources expose data as URIs that the client can read. They are useful for static or frequently accessed data.

| Resource URI | Description | MIME Type | Content |
|--------------|-------------|-----------|---------|
| `pdf://categories` | Full category tree | `application/json` | JSON tree |
| `pdf://statistics` | Overall statistics | `application/json` | JSON stats |
| `pdf://folders` | List of all folders with counts | `application/json` | JSON array |
| `pdf://weekly/{weeks_ago}` | Weekly changes for a specific week | `application/json` | JSON diff |
| `pdf://document/{path}` | Document metadata (URL‑encoded path) | `application/json` | JSON PDFFile |
| `pdf://findings` | Current interesting findings | `application/json` | JSON list |
| `pdf://duplicates` | Duplicate groups | `application/json` | JSON groups |

Resources are read‑only and are served when the client requests them.

---

## 6. Prompt Definitions

Prompts are templates that help the user interact with the system. They can include placeholders for arguments.

| Prompt Name | Description | Template |
|-------------|-------------|----------|
| `summarize_folder` | Summarize a folder's contents | "Give me a summary of the folder `{folder}` including its size, categories, and any interesting findings." |
| `find_related` | Find documents similar to a given one | "I have a document at `{path}`. Can you find other documents that are similar and tell me why they are related?" |
| `weekly_digest` | Generate a digest of weekly changes | "What changed in my PDF inventory over the past week? Highlight new, modified, and deleted files." |
| `classify_unknown` | Help classify a document | "I have an unknown document `{filename}`. Can you suggest possible categories based on its content and metadata?" |

Prompts are templates that the client can render and send as messages to the assistant.

---

## 7. Integration Plan

1. **Standalone deployment**: The MCP Bridge runs as a separate process (e.g., via `mcp run`). It reads from the existing SQLite database and communicates with IAM if deployed.
2. **No changes to core**: The bridge uses only the read‑only interfaces of the existing modules. No new tables, no writes.
3. **Configuration**: The bridge reads the same configuration as the main application (database path, IAM endpoint). It can be started independently.
4. **MCP server library**: Use the official `mcp` Python SDK (or a lightweight custom implementation) to handle JSON‑RPC and stdio/HTTP transport.
5. **Testing**: Unit tests for each adapter with mock data access; integration tests against a real database.
6. **Documentation**: Provide a user guide on how to configure MCP hosts (Claude Desktop, VS Code) to connect to the bridge.

---

## 8. Security Considerations

- **Read‑only**: The bridge only performs SELECT queries. It does not have write access to the database.
- **No authentication/authorization** in v1: The bridge trusts the MCP host and the local environment. In future, we could add token‑based authentication if exposed over network.
- **Path traversal**: When accepting file paths as input, ensure they are sanitized and validated against the known database to prevent injection (though database is read‑only, injection could crash the query).
- **IAM endpoint**: If IAM is remote, ensure HTTPS and possibly API keys.
- **Logging**: Log all tool invocations for audit; avoid logging sensitive document content.
- **Rate limiting**: Not required for local use, but if exposed over network, we may add throttling.
- **Environment isolation**: Run the bridge with minimal permissions (read‑only user).

---

## 9. Example MCP Requests/Responses

### Request: search_documents
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_documents",
    "arguments": {
      "query": "invoice",
      "limit": 5
    }
  }
}
```

### Response:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Found 5 documents matching 'invoice':\n1. /path/to/invoice1.pdf (Confidence: 0.95, Category: Bill)\n2. /path/to/invoice2.pdf (Confidence: 0.87, Category: Bill)\n..."
      }
    ],
    "isError": false
  }
}
```

### Request: get_document
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "resources/read",
  "params": {
    "uri": "pdf://document//path%2Fto%2Fdocument.pdf"
  }
}
```

### Response:
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "contents": [
      {
        "uri": "pdf://document//path%2Fto%2Fdocument.pdf",
        "mimeType": "application/json",
        "text": "{\"path\":\"/path/to/document.pdf\",\"filename\":\"document.pdf\",\"category\":\"Research\",\"confidence\":0.78,...}"
      }
    ]
  }
}
```

### Prompt request: weekly_digest
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "prompts/get",
  "params": {
    "name": "weekly_digest",
    "arguments": {}
  }
}
```

### Response:
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "description": "Weekly digest prompt",
    "messages": [
      {
        "role": "user",
        "content": {
          "type": "text",
          "text": "What changed in my PDF inventory over the past week? Highlight new, modified, and deleted files."
        }
      }
    ]
  }
}
```

---

