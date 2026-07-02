import os
import sqlite3
import json
import re
from typing import Dict, Any, List


def _get_db_path() -> str:
    return os.environ.get("PDF_DB", "pdf_cache.db")


def parse_search_query(q: str) -> Dict[str, Any]:
    """Parse search query with tag syntax. 
    
    Examples:
    - topic:python
    - type:book
    - author:Goodfellow
    - year>2021
    - confidence>90
    - duplicate:false
    """
    filters = {
        "text": [],
        "topics": [],
        "category": None,
        "author": None,
        "confidence_min": None,
        "duplicate": None,
    }
    
    # Parse tags
    tag_pattern = r'(\w+):([^\s]+)'
    comparison_pattern = r'(\w+)([><=!]+)([\d.]+)'
    
    for tag_match in re.finditer(tag_pattern, q):
        key, value = tag_match.groups()
        if key == "topic":
            filters["topics"].append(value)
        elif key == "type":
            filters["category"] = value
        elif key == "author":
            filters["author"] = value
        elif key == "duplicate":
            filters["duplicate"] = value.lower() in ("true", "yes", "1")
    
    for comp_match in re.finditer(comparison_pattern, q):
        key, op, value = comp_match.groups()
        if key == "confidence" and op == ">":
            filters["confidence_min"] = float(value)
    
    # Remove tags from query, keep plain text
    plain_q = re.sub(tag_pattern, '', q).strip()
    if plain_q:
        filters["text"].append(plain_q)
    
    return filters


def search_documents(q: str, page: int = 1, limit: int = 50) -> Dict[str, Any]:
    """Search documents with tag-based query syntax."""
    db_path = _get_db_path()
    offset = (page - 1) * limit
    filters = parse_search_query(q)
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Build SQL query
        where_clauses = ["1=1"]
        params = []
        
        # Text search
        for text_q in filters["text"]:
            like = f"%{text_q}%"
            where_clauses.append("(filename LIKE ? OR title LIKE ? OR author LIKE ?)")
            params.extend([like, like, like])
        
        # Category filter
        if filters["category"]:
            where_clauses.append("category = ?")
            params.append(filters["category"])
        
        # Author filter
        if filters["author"]:
            where_clauses.append("author LIKE ?")
            params.append(f"%{filters['author']}%")
        
        # Confidence filter
        if filters["confidence_min"] is not None:
            where_clauses.append("confidence >= ?")
            params.append(filters["confidence_min"])
        
        where_sql = " AND ".join(where_clauses)
        
        # Get count
        count_sql = f"SELECT COUNT(*) FROM pdf_cache WHERE {where_sql}"
        cur.execute(count_sql, params)
        total = cur.fetchone()[0]
        
        # Get documents
        data_sql = f"""
            SELECT path, filename, title, author, confidence, modified_time, size_bytes, topics_json 
            FROM pdf_cache 
            WHERE {where_sql} 
            ORDER BY confidence DESC, modified_time DESC 
            LIMIT ? OFFSET ?
        """
        cur.execute(data_sql, params + [limit, offset])
        rows = cur.fetchall()
        
        items = []
        for row in rows:
            # Check topic filters
            topics_json = row[7]
            topics = []
            if topics_json:
                try:
                    topics = json.loads(topics_json) if isinstance(topics_json, str) else topics_json
                except (json.JSONDecodeError, TypeError):
                    topics = []
            
            # Skip if topic filter doesn't match
            if filters["topics"] and not any(t in topics for t in filters["topics"]):
                continue
            
            items.append({
                "id": row[0],
                "filename": row[1],
                "title": row[2],
                "author": row[3],
                "confidence": row[4],
                "modified_time": row[5],
                "size": row[6],
                "topics": topics,
            })
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "query": q,
            "filters": filters,
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_search_suggestions(partial: str = "") -> Dict[str, Any]:
    """Get autocomplete suggestions for search (topics, authors, categories)."""
    db_path = _get_db_path()
    
    suggestions = {
        "topics": [],
        "authors": [],
        "categories": [],
        "prefixes": ["topic:", "type:", "author:", "confidence>"],
    }
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get unique topics
        cur.execute("SELECT topics_json FROM pdf_cache WHERE topics_json IS NOT NULL")
        topics_set = set()
        for (topics_json,) in cur.fetchall():
            if topics_json:
                try:
                    topics = json.loads(topics_json) if isinstance(topics_json, str) else topics_json
                    if isinstance(topics, list):
                        topics_set.update(topics)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        suggestions["topics"] = sorted(list(topics_set))[:20]
        
        # Get unique authors
        cur.execute("SELECT DISTINCT author FROM pdf_cache WHERE author IS NOT NULL ORDER BY author")
        suggestions["authors"] = [row[0] for row in cur.fetchall() if row[0]][:20]
        
        # Get unique categories
        cur.execute("SELECT DISTINCT category FROM pdf_cache WHERE category IS NOT NULL ORDER BY category")
        suggestions["categories"] = [row[0] for row in cur.fetchall() if row[0]][:20]
        
        return suggestions
    finally:
        try:
            conn.close()
        except Exception:
            pass
