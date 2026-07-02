"""All MCP tool adapters. Each wraps a ReadOnlySQLite query and formats output for MCP."""
import json
from typing import Dict, Any
from .base import BaseAdapter


def _text(data) -> Dict:
    return {"content": [{"type": "text", "text": json.dumps(data, default=str, indent=2)}]}


class SearchAdapter(BaseAdapter):
    async def execute(self, params: Dict[str, Any]) -> Dict:
        query = params.get("query", "")
        limit = int(params.get("limit", 20))
        results = self.db.search_documents(query, limit)
        return _text({"query": query, "results": results, "count": len(results)})


class DocumentAdapter(BaseAdapter):
    async def execute(self, params: Dict[str, Any]) -> Dict:
        path = params.get("path", "")
        doc = self.db.get_document(path)
        if not doc:
            return _text({"error": f"No document found for path: {path}"})
        return _text(doc)


class CategoryAdapter(BaseAdapter):
    async def execute(self, params: Dict[str, Any]) -> Dict:
        rows = self.db.get_categories()
        # Build hierarchy: {category: {subcategory: count}}
        hierarchy: Dict[str, Any] = {}
        for row in rows:
            cat = row["category"] or "Unknown"
            sub = row["subcategory"] or "_"
            hierarchy.setdefault(cat, {})[sub] = row["count"]
        return _text(hierarchy)


class DuplicateAdapter(BaseAdapter):
    async def execute(self, params: Dict[str, Any]) -> Dict:
        rows = self.db.get_duplicates()
        result = [
            {"file_hash": r["file_hash"], "count": r["count"],
             "paths": r["paths"].split("||")}
            for r in rows
        ]
        return _text({"duplicate_groups": result, "total_groups": len(result)})


class FolderAdapter(BaseAdapter):
    async def execute(self, params: Dict[str, Any]) -> Dict:
        rows = self.db.get_folder_stats()
        return _text({"folders": rows, "total_folders": len(rows)})


class StatsAdapter(BaseAdapter):
    async def execute(self, params: Dict[str, Any]) -> Dict:
        stats = self.db.get_stats()
        cats = self.db.get_categories()
        category_counts = {}
        for row in cats:
            cat = row["category"] or "Unknown"
            category_counts[cat] = category_counts.get(cat, 0) + row["count"]
        stats["categories"] = category_counts
        return _text(stats)


class WeeklyAdapter(BaseAdapter):
    """Returns the most recently modified PDFs — closest thing to a weekly digest without a scheduler."""
    async def execute(self, params: Dict[str, Any]) -> Dict:
        limit = int(params.get("limit", 20))
        rows = self.db.get_recent(limit)
        return _text({"recent_documents": rows, "count": len(rows)})


class FindingsAdapter(BaseAdapter):
    """Returns low-confidence classifications as findings that need attention."""
    async def execute(self, params: Dict[str, Any]) -> Dict:
        threshold = float(params.get("threshold", 0.4))
        limit = int(params.get("limit", 50))
        rows = self.db.get_low_confidence(threshold, limit)
        findings = [
            {"path": r["path"], "filename": r["filename"],
             "category": r["category"], "confidence": r["confidence"],
             "finding": "Low classification confidence — may need review"}
            for r in rows
        ]
        duplicates = self.db.get_duplicates()
        for d in duplicates:
            for path in d["paths"].split("||"):
                findings.append({"path": path, "finding": "Duplicate file", "file_hash": d["file_hash"]})
        return _text({"findings": findings, "count": len(findings)})


class SimilarityAdapter(BaseAdapter):
    async def execute(self, params: Dict[str, Any]) -> Dict:
        category = params.get("category", "")
        limit = int(params.get("limit", 10))
        if not category:
            return _text({"error": "Provide a 'category' param to find similar documents."})
        rows = self.db.get_similar_by_category(category, limit)
        return _text({"category": category, "similar": rows})


class MetadataAdapter(BaseAdapter):
    async def execute(self, params: Dict[str, Any]) -> Dict:
        path = params.get("path", "")
        doc = self.db.get_document(path)
        if not doc:
            return _text({"error": f"Not found: {path}"})
        return _text({k: v for k, v in doc.items()})


class ConfidenceAdapter(BaseAdapter):
    async def execute(self, params: Dict[str, Any]) -> Dict:
        rows = self.db.get_low_confidence(threshold=1.1, limit=10000)  # all rows
        buckets = {"high (>=0.8)": 0, "medium (0.4-0.8)": 0, "low (<0.4)": 0}
        for r in rows:
            c = r.get("confidence", 0) or 0
            if c >= 0.8:
                buckets["high (>=0.8)"] += 1
            elif c >= 0.4:
                buckets["medium (0.4-0.8)"] += 1
            else:
                buckets["low (<0.4)"] += 1
        return _text({"confidence_distribution": buckets})
