import os
import sqlite3
import json
from typing import Dict, Any, List


def _get_db_path() -> str:
    return os.environ.get("PDF_DB", "pdf_cache.db")


def get_topics() -> Dict[str, Any]:
    """Get all topics from document topics_json field. Returns aggregated topic counts."""
    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # Get all documents with topics
        cur.execute("SELECT topics_json FROM pdf_cache WHERE topics_json IS NOT NULL")
        rows = cur.fetchall()
        
        topic_counts = {}
        for (topics_json,) in rows:
            if topics_json:
                try:
                    topics = json.loads(topics_json) if isinstance(topics_json, str) else topics_json
                    if isinstance(topics, list):
                        for topic in topics:
                            topic_counts[topic] = topic_counts.get(topic, 0) + 1
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Convert to list and sort by count
        topics_list = [{"name": t, "count": c} for t, c in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)]
        return {"topics": topics_list, "total": len(topics_list)}
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_topic_documents(topic: str, page: int = 1, limit: int = 50) -> Dict[str, Any]:
    """Get documents associated with a specific topic."""
    db_path = _get_db_path()
    offset = (page - 1) * limit
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get all docs and filter by topic in Python (SQLite JSON is limited)
        cur.execute("SELECT path, filename, title, author, confidence, modified_time, size_bytes, topics_json FROM pdf_cache ORDER BY modified_time DESC")
        all_rows = cur.fetchall()
        
        # Filter by topic
        filtered = []
        for row in all_rows:
            topics_json = row[7]
            if topics_json:
                try:
                    topics = json.loads(topics_json) if isinstance(topics_json, str) else topics_json
                    if isinstance(topics, list) and topic in topics:
                        filtered.append(row)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        total = len(filtered)
        items = []
        for row in filtered[offset:offset+limit]:
            items.append({
                "id": row[0],
                "filename": row[1],
                "title": row[2],
                "author": row[3],
                "confidence": row[4],
                "modified_time": row[5],
                "size": row[6],
            })
        
        return {"items": items, "total": total, "page": page, "limit": limit, "topic": topic}
    finally:
        try:
            conn.close()
        except Exception:
            pass
