import os
import sqlite3
from typing import Dict, Any


def _row_to_dict(row) -> Dict[str, Any]:
    return {
        "id": row[0],
        "filename": row[1],
        "title": row[8],
        "author": row[9],
        "confidence": row[14],
        "category": row[12],
        "subcategory": row[13],
        "modified_time": row[5],
        "size": row[3],
    }


def _get_db_path() -> str:
    """Return SQLite db path. Can be overridden by env PDF_DB."""
    return os.environ.get("PDF_DB", "pdf_inventory.db")


def list_documents(page: int = 1, limit: int = 50, q: str = None, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Server-side SQL pagination against the `pdf_cache` table.

    Supports basic `q` free-text matching (filename/title/author) and `filters` dict keys: `category`, `confidence_min`.
    """
    db_path = _get_db_path()
    offset = (page - 1) * limit

    where_clauses = ["1=1"]
    params = []

    if q:
        like = f"%{q}%"
        where_clauses.append("(filename LIKE ? OR title LIKE ? OR author LIKE ?)")
        params.extend([like, like, like])

    if filters:
        if "category" in filters and filters.get("category"):
            where_clauses.append("category = ?")
            params.append(filters["category"])
        if "confidence_min" in filters and filters.get("confidence_min") is not None:
            where_clauses.append("confidence >= ?")
            params.append(float(filters["confidence_min"]))

    where_sql = " AND ".join(where_clauses)

    count_sql = f"SELECT COUNT(*) FROM pdf_cache WHERE {where_sql}"
    data_sql = f"SELECT path, filename, parent_folder, size_bytes, created_time, modified_time, file_hash, page_count, title, author, subject, keywords, category, subcategory, confidence, flags, classification_explanation FROM pdf_cache WHERE {where_sql} ORDER BY modified_time DESC LIMIT ? OFFSET ?"

    items = []
    total = 0
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(count_sql, params)
        total = cur.fetchone()[0]

        cur.execute(data_sql, params + [limit, offset])
        rows = cur.fetchall()
        items = [_row_to_dict(r) for r in rows]
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return {"items": items, "total": total, "page": page, "limit": limit}


def get_document(doc_id: str) -> Dict[str, Any]:
    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT path, filename, parent_folder, size_bytes, created_time, modified_time, file_hash, page_count, title, author, subject, keywords, category, subcategory, confidence, flags, classification_explanation FROM pdf_cache WHERE path = ? OR filename = ?", (doc_id, doc_id))
        row = cur.fetchone()
        if not row:
            return None
        return _row_to_dict(row)
    finally:
        try:
            conn.close()
        except Exception:
            pass
