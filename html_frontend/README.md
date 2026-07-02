# PDF Explorer – HTML Frontend

A modern, Python-first web interface for browsing and exploring your PDF inventory.

## Stack

- **Backend:** FastAPI (REST API)
- **Templating:** Jinja2 (server-side rendering)
- **Frontend:** HTMX (dynamic fragments) + Chart.js (charts)
- **Database:** SQLite (cached PDF metadata)
- **Testing:** pytest + FastAPI TestClient

## Features (Phase A – Core Implementation)

- ✅ **Dashboard:** Key metrics, storage/category charts
- ✅ **Document Explorer:** Paginated table with search & filtering
- ✅ **Document Detail:** Full metadata, classification, relationships
- ✅ **Charts:** Storage distribution, category breakdown
- ✅ **Adapters:** Clean integration with backend (no logic duplication)
- ⏳ **Categories Explorer:** Hierarchical browser (Phase B)
- ⏳ **Topics Explorer:** Topic drill-down with relationships (Phase B)
- ⏳ **Similarity Explorer:** IAM-powered graph + clusters (Phase B)
- ⏳ **Duplicate Groups:** Duplicate visualization (Phase B)
- ⏳ **Reports:** Export to Markdown, HTML, CSV, JSON (Phase B)

## Quick Start

### Install Dependencies

```bash
pip install fastapi uvicorn jinja2
```

### Run Development Server

```bash
cd html_frontend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Then open: **http://localhost:8000**

### Run Tests

```bash
cd .. # project root
python -m pytest unit/test_frontend_adapters.py -v
python -m pytest unit/test_api_endpoints.py -v
```

## Architecture

See [frontend_design.md](./frontend_design.md) for the complete architecture:
- Information Architecture (14 page types, progressive enhancement SPA)
- UI Wireframes (text descriptions for all key screens)
- Component Hierarchy (Jinja2 templates, HTMX partials)
- REST API Design (detailed endpoints under `/api/v1`)
- Backend Integration Plan (adapter pattern, no duplication)
- Database Queries (SQL pagination, indexes, FTS5)
- Performance Strategy (lazy loading, caching, background jobs)
- Security Considerations (local-first, optional auth)

See [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) for:
- Phase A deliverables (what's built)
- Phase B roadmap (what's next)
- Code structure and testing guide

## Environment Variables

- `PDF_DB` – Path to SQLite cache DB (default: `pdf_cache.db`)

Example:
```bash
export PDF_DB=/path/to/my/pdf_inventory.db
python -m uvicorn app:app --reload
```

## API Endpoints

### Documents
- `GET /api/documents` – Paginated list (query params: `page`, `limit`, `q`, filters)
- `GET /api/documents/{doc_id}` – Single document detail

### Stats & Charts
- `GET /api/stats` – Overall statistics
- `GET /api/charts/storage` – Storage distribution (Chart.js format)
- `GET /api/charts/categories` – Category distribution (Chart.js format)

### Pages (HTML)
- `GET /` – Dashboard
- `GET /documents` – Document explorer
- `GET /documents/{id}` – Document detail page
- `GET /categories`, `/topics`, `/duplicates`, `/similarity`, `/findings` – Stubs (Phase B)

## Project Structure

```
html_frontend/
├── app.py                      # FastAPI entrypoint
├── config.py                   # AppConfig loader
├── adapters/                   # Backend integration layer
│   ├── __init__.py
│   ├── documents.py            # SQL-based pagination & filtering
│   └── stats.py                # Statistics wrapper
├── api/                        # FastAPI routers
│   ├── __init__.py
│   ├── stats.py                # /api/stats endpoint
│   ├── documents.py            # /api/documents endpoint
│   ├── charts.py               # /api/charts/* endpoints
│   └── (stubs for categories, topics, etc.)
├── templates/                  # Jinja2 templates
│   ├── base.html               # Shell layout
│   ├── dashboard.html
│   ├── documents.html
│   ├── document_detail.html
│   └── fragments/
│       ├── documents_table.html
│       ├── stats.html
│       └── document_detail_fragment.html
├── static/                     # CSS, JS
│   ├── css/main.css
│   └── js/htmx-helpers.js
├── frontend_design.md          # Architecture (authoritative)
├── IMPLEMENTATION_SUMMARY.md   # Deliverables & roadmap
└── README.md                   # This file

unit/
├── test_frontend_adapters.py   # Adapter unit tests (3 tests, all passing)
└── test_api_endpoints.py       # API endpoint integration tests
```

## Key Design Principles

### 1. Adapter Pattern
All backend calls go through adapters in `html_frontend/adapters/`. This ensures:
- **No duplication:** Business logic stays in the backend
- **Clean API:** Adapters return simple dicts for templates/JSON
- **Testable:** Adapters use env var overrides (`PDF_DB`) for test fixtures

### 2. Server-Side Pagination
- SQL `LIMIT`/`OFFSET` queries for document lists
- Supports filtering by query (LIKE) and category/confidence
- Keyset pagination pattern available for scale

### 3. HTMX + Fragment Rendering
- API endpoints detect `HX-Request` header
- Return HTML fragments for HTMX swaps instead of JSON
- Minimal client-side JS; progressive enhancement

### 4. Chart.js Data Endpoints
- `/api/charts/*` endpoints return raw data (labels, values)
- Frontend fetches and renders with Chart.js client-side
- Decouples chart rendering from backend

## Testing

### Adapter Tests
```bash
python -m pytest unit/test_frontend_adapters.py -v
```
Tests:
- Pagination (basic list)
- Query filtering (filename/title/author)
- Offset pagination (page 2 etc.)

### API Tests
```bash
python -m pytest unit/test_api_endpoints.py -v
```
Tests:
- JSON document endpoint
- Document detail fetch
- Stats endpoint

All tests use temporary SQLite fixtures and env var override (`PDF_DB`).

## Performance

- **Lazy loading:** Charts and tables load on-demand via HTMX
- **Server pagination:** SQL `LIMIT`/`OFFSET` for large datasets
- **Caching:** Frequent stats cached in-memory (TODO: Phase B)
- **Database indices:** Recommended for `category`, `confidence`, `modified_time`

## Security

**Default:** Local single-user mode (no authentication).

To add authentication (Phase B):
- FastAPI OAuth2PasswordBearer middleware
- CSRF tokens for form submissions
- XSS protection via Jinja2 auto-escape (enabled by default)
- SQL injection protection via parameterised queries (enforced)

## Roadmap

### Phase B (Feature Completion)
- [ ] Category/topic/similarity explorers with charts
- [ ] Advanced search (tag syntax: `topic:python type:book`)
- [ ] Report generation (HTML, Markdown, CSV, JSON)
- [ ] FTS5 full-text search integration
- [ ] In-memory caching layer (LRU + TTL)
- [ ] Background job queue for expensive tasks
- [ ] DataTables.js for column control
- [ ] Responsive mobile layout

### Phase C (Hardening & Deployment)
- [ ] OAuth2 / basic auth middleware
- [ ] Docker image & deployment guide
- [ ] Environment configuration (settings.yaml)
- [ ] Kubernetes manifests (optional)

## Contributing

- **Keep adapters focused:** One responsibility per adapter function
- **No backend logic:** All changes should be in `html_frontend/` only
- **Test with fixtures:** Use temp SQLite + env var override for adapter tests
- **Use HTMX:** Prefer HTMX fragments for dynamic updates over client-side JS

## Support

See [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) for:
- File structure details
- Code examples
- Architecture decisions
- Next steps

## License

Same as main PDF Explorer project.
