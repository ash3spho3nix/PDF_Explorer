import sqlite3
from typing import List, Dict, Any, Optional
import json
from pathlib import Path


class ReadOnlySQLite:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _query(self, sql: str, params=()) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def search_documents(self, query: str, limit: int) -> List[Dict]:
        sql = """
        SELECT path, filename, category, subcategory, confidence, title, author, page_count, size_bytes
        FROM pdf_cache
        WHERE filename LIKE ? OR title LIKE ? OR author LIKE ? OR category LIKE ?
        ORDER BY confidence DESC
        LIMIT ?
        """
        like = f"%{query}%"
        return self._query(sql, (like, like, like, like, limit))

    def get_document(self, path: str) -> Optional[Dict]:
        rows = self._query("SELECT * FROM pdf_cache WHERE path = ?", (path,))
        return rows[0] if rows else None

    def get_categories(self) -> List[Dict]:
        return self._query(
            "SELECT category, subcategory, COUNT(*) as count FROM pdf_cache GROUP BY category, subcategory ORDER BY category"
        )

    def get_duplicates(self) -> List[Dict]:
        """Return files sharing the same file_hash (non-null)."""
        return self._query(
            """
            SELECT file_hash, COUNT(*) as count, GROUP_CONCAT(path, '||') as paths
            FROM pdf_cache
            WHERE file_hash IS NOT NULL AND file_hash != ''
            GROUP BY file_hash
            HAVING count > 1
            ORDER BY count DESC
            """
        )

    def get_folder_stats(self) -> List[Dict]:
        return self._query(
            """
            SELECT parent_folder,
                   COUNT(*) as total_files,
                   SUM(size_bytes) as total_size,
                   AVG(confidence) as avg_confidence
            FROM pdf_cache
            GROUP BY parent_folder
            ORDER BY total_files DESC
            """
        )

    def get_stats(self) -> Dict:
        rows = self._query(
            "SELECT COUNT(*) as total, SUM(size_bytes) as total_size, AVG(confidence) as avg_confidence FROM pdf_cache"
        )
        return rows[0] if rows else {}

    def get_recent(self, limit: int = 20) -> List[Dict]:
        return self._query(
            "SELECT path, filename, category, subcategory, modified_time FROM pdf_cache ORDER BY modified_time DESC LIMIT ?",
            (limit,)
        )

    def get_low_confidence(self, threshold: float = 0.4, limit: int = 50) -> List[Dict]:
        return self._query(
            "SELECT path, filename, category, confidence FROM pdf_cache WHERE confidence < ? ORDER BY confidence ASC LIMIT ?",
            (threshold, limit)
        )

    def get_similar_by_category(self, category: str, limit: int = 10) -> List[Dict]:
        return self._query(
            "SELECT path, filename, title, author, confidence FROM pdf_cache WHERE category = ? ORDER BY confidence DESC LIMIT ?",
            (category, limit)
        )