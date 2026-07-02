import os
import sqlite3
from typing import Dict, Any, List


def _get_db_path() -> str:
    return os.environ.get("PDF_DB", "pdf_cache.db")


def get_categories() -> Dict[str, Any]:
    """Get hierarchical category tree with document counts."""
    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # Get category and subcategory counts
        cur.execute("""
            SELECT category, subcategory, COUNT(*) as count 
            FROM pdf_cache 
            WHERE category IS NOT NULL 
            GROUP BY category, subcategory 
            ORDER BY category, subcategory
        """)
        rows = cur.fetchall()
        
        # Build hierarchical structure
        categories = {}
        for category, subcategory, count in rows:
            if category not in categories:
                categories[category] = {"count": 0, "subcategories": {}}
            if subcategory:
                categories[category]["subcategories"][subcategory] = count
            categories[category]["count"] += count
        
        return {"categories": categories}
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_category_documents(category: str, subcategory: str = None, page: int = 1, limit: int = 50) -> Dict[str, Any]:
    """Get documents for a specific category/subcategory."""
    db_path = _get_db_path()
    offset = (page - 1) * limit
    
    where_clauses = ["category = ?"]
    params = [category]
    
    if subcategory:
        where_clauses.append("subcategory = ?")
        params.append(subcategory)
    
    where_sql = " AND ".join(where_clauses)
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get count
        count_sql = f"SELECT COUNT(*) FROM pdf_cache WHERE {where_sql}"
        cur.execute(count_sql, params)
        total = cur.fetchone()[0]
        
        # Get documents
        data_sql = f"""
            SELECT path, filename, title, author, confidence, modified_time, size_bytes 
            FROM pdf_cache 
            WHERE {where_sql} 
            ORDER BY modified_time DESC 
            LIMIT ? OFFSET ?
        """
        cur.execute(data_sql, params + [limit, offset])
        rows = cur.fetchall()
        
        items = []
        for row in rows:
            items.append({
                "id": row[0],
                "filename": row[1],
                "title": row[2],
                "author": row[3],
                "confidence": row[4],
                "modified_time": row[5],
                "size": row[6],
            })
        
        return {"items": items, "total": total, "page": page, "limit": limit, "category": category, "subcategory": subcategory}
    finally:
        try:
            conn.close()
        except Exception:
            pass
