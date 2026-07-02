import os
import sqlite3
from typing import Dict, Any, List


def _get_db_path() -> str:
    return os.environ.get("PDF_DB", "pdf_cache.db")


def get_duplicates() -> Dict[str, Any]:
    """Get duplicate groups. Duplicates are identified by same hash or similar filename."""
    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Find groups by file_hash (exact matches)
        cur.execute("""
            SELECT file_hash, COUNT(*) as count 
            FROM pdf_cache 
            WHERE file_hash IS NOT NULL 
            GROUP BY file_hash 
            HAVING count > 1 
            ORDER BY count DESC
        """)
        hash_groups = cur.fetchall()
        
        duplicate_groups = []
        for file_hash, count in hash_groups:
            if file_hash:
                cur.execute("SELECT path, filename, size_bytes, modified_time FROM pdf_cache WHERE file_hash = ? ORDER BY modified_time DESC", (file_hash,))
                docs = cur.fetchall()
                group = {
                    "type": "hash",
                    "hash": file_hash,
                    "count": count,
                    "documents": [
                        {"id": d[0], "filename": d[1], "size": d[2], "modified_time": d[3]}
                        for d in docs
                    ]
                }
                duplicate_groups.append(group)
        
        return {"groups": duplicate_groups, "total": len(duplicate_groups)}
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_duplicate_group(group_id: str) -> Dict[str, Any]:
    """Get a specific duplicate group by hash."""
    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT path, filename, title, author, size_bytes, modified_time, category, confidence 
            FROM pdf_cache 
            WHERE file_hash = ? 
            ORDER BY modified_time DESC
        """, (group_id,))
        rows = cur.fetchall()
        
        if not rows:
            return {"error": "group not found"}
        
        documents = []
        for row in rows:
            documents.append({
                "id": row[0],
                "filename": row[1],
                "title": row[2],
                "author": row[3],
                "size": row[4],
                "modified_time": row[5],
                "category": row[6],
                "confidence": row[7],
            })
        
        return {
            "group_id": group_id,
            "type": "hash",
            "count": len(documents),
            "documents": documents
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass
