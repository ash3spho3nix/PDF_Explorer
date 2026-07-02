import os
import sqlite3
import json
import csv
from io import StringIO
from typing import Dict, Any
from datetime import datetime


def _get_db_path() -> str:
    return os.environ.get("PDF_DB", "pdf_cache.db")


def get_all_documents_for_export() -> list:
    """Get all documents from cache for report generation."""
    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT path, filename, title, author, category, subcategory, confidence, 
                   modified_time, size_bytes, page_count 
            FROM pdf_cache 
            ORDER BY modified_time DESC
        """)
        return cur.fetchall()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def generate_html_report() -> str:
    """Generate an HTML report of all documents."""
    docs = get_all_documents_for_export()
    
    html = """<!DOCTYPE html>
<html>
<head>
    <title>PDF Inventory Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #f4f4f4; }
        .summary { margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>PDF Inventory Report</h1>
    <div class="summary">
        <p><strong>Generated:</strong> """ + datetime.now().isoformat() + """</p>
        <p><strong>Total Documents:</strong> """ + str(len(docs)) + """</p>
    </div>
    <table>
        <thead>
            <tr>
                <th>Filename</th>
                <th>Title</th>
                <th>Author</th>
                <th>Category</th>
                <th>Confidence</th>
                <th>Pages</th>
                <th>Size (bytes)</th>
                <th>Modified</th>
            </tr>
        </thead>
        <tbody>
"""
    for doc in docs:
        html += f"""            <tr>
                <td>{doc[1]}</td>
                <td>{doc[2] or '-'}</td>
                <td>{doc[3] or '-'}</td>
                <td>{doc[4] or '-'}</td>
                <td>{doc[6]:.0f}%</td>
                <td>{doc[9] or '-'}</td>
                <td>{doc[8]:,}</td>
                <td>{doc[7]}</td>
            </tr>
"""
    
    html += """        </tbody>
    </table>
</body>
</html>
"""
    return html


def generate_markdown_report() -> str:
    """Generate a Markdown report of all documents."""
    docs = get_all_documents_for_export()
    
    md = f"""# PDF Inventory Report

**Generated:** {datetime.now().isoformat()}  
**Total Documents:** {len(docs)}

## Documents

| Filename | Title | Author | Category | Confidence | Pages |
|----------|-------|--------|----------|------------|-------|
"""
    
    for doc in docs:
        md += f"| {doc[1]} | {doc[2] or '-'} | {doc[3] or '-'} | {doc[4] or '-'} | {doc[6]:.0f}% | {doc[9] or '-'} |\n"
    
    return md


def generate_csv_report() -> str:
    """Generate a CSV report of all documents."""
    docs = get_all_documents_for_export()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Path", "Filename", "Title", "Author", "Category", "Subcategory",
        "Confidence", "Modified", "Size (bytes)", "Pages"
    ])
    
    for doc in docs:
        writer.writerow(doc)
    
    return output.getvalue()


def generate_json_report() -> str:
    """Generate a JSON report of all documents."""
    docs = get_all_documents_for_export()
    
    data = {
        "generated": datetime.now().isoformat(),
        "total": len(docs),
        "documents": [
            {
                "path": doc[0],
                "filename": doc[1],
                "title": doc[2],
                "author": doc[3],
                "category": doc[4],
                "subcategory": doc[5],
                "confidence": doc[6],
                "modified_time": doc[7],
                "size": doc[8],
                "pages": doc[9],
            }
            for doc in docs
        ]
    }
    
    return json.dumps(data, indent=2)


def generate_report(format: str = "html") -> Dict[str, Any]:
    """Generate a report in the specified format."""
    if format == "html":
        return {"content": generate_html_report(), "content_type": "text/html"}
    elif format == "markdown" or format == "md":
        return {"content": generate_markdown_report(), "content_type": "text/markdown"}
    elif format == "csv":
        return {"content": generate_csv_report(), "content_type": "text/csv"}
    elif format == "json":
        return {"content": generate_json_report(), "content_type": "application/json"}
    else:
        return {"error": "unsupported format", "supported": ["html", "markdown", "csv", "json"]}
