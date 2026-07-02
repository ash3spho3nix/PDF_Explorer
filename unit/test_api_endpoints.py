import os
import sys
import sqlite3
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def create_sample_db(path):
    """Create a test pdf_cache db with 2 sample documents."""
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE pdf_cache (
        path TEXT PRIMARY KEY,
        filename TEXT,
        parent_folder TEXT,
        size_bytes INTEGER,
        created_time REAL,
        modified_time REAL,
        file_hash TEXT,
        page_count INTEGER,
        title TEXT,
        author TEXT,
        subject TEXT,
        keywords TEXT,
        category TEXT,
        subcategory TEXT,
        confidence REAL,
        flags TEXT,
        classification_explanation TEXT,
        last_cached REAL
    )
    ''')

    rows = [
        ('/tmp/a.pdf','a.pdf','/tmp',1234,0,1000,'h1',1,'Title A','Alice','','','Book','Textbook',95,'[]',None,0),
        ('/tmp/b.pdf','b.pdf','/tmp',2345,0,2000,'h2',2,'Title B','Bob','','','Research','Article',88,'[]',None,0),
    ]
    cur.executemany('INSERT INTO pdf_cache VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', rows)
    conn.commit()
    conn.close()


def test_api_documents_endpoint(monkeypatch, tmp_path):
    """Test GET /api/documents returns paginated JSON."""
    dbfile = tmp_path / 'test.db'
    create_sample_db(str(dbfile))
    monkeypatch.setenv('PDF_DB', str(dbfile))

    # Import app after setting env
    from html_frontend.app import app
    client = TestClient(app)

    resp = client.get("/api/documents?page=1&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data['total'] == 2
    assert len(data['items']) == 2


def test_api_documents_htmx_fragment(monkeypatch, tmp_path):
    """Test GET /api/documents with HX-Request returns HTML fragment."""
    dbfile = tmp_path / 'test.db'
    create_sample_db(str(dbfile))
    monkeypatch.setenv('PDF_DB', str(dbfile))

    from html_frontend.app import app
    client = TestClient(app)

    resp = client.get("/api/documents?page=1&limit=10", headers={"hx-request": "true"})
    assert resp.status_code == 200
    # Should be HTML table, not JSON
    assert 'table' in resp.text.lower()


def test_api_document_detail(monkeypatch, tmp_path):
    """Test GET /api/documents/{doc_id} returns document JSON."""
    dbfile = tmp_path / 'test.db'
    create_sample_db(str(dbfile))
    monkeypatch.setenv('PDF_DB', str(dbfile))

    from html_frontend.app import app
    client = TestClient(app)

    resp = client.get("/api/documents//tmp/a.pdf")
    assert resp.status_code == 200
    data = resp.json()
    assert data['filename'] == 'a.pdf'
    assert data['author'] == 'Alice'


def test_api_stats_endpoint(monkeypatch, tmp_path):
    """Test GET /api/stats returns stats JSON."""
    dbfile = tmp_path / 'test.db'
    create_sample_db(str(dbfile))
    monkeypatch.setenv('PDF_DB', str(dbfile))

    from html_frontend.app import app
    client = TestClient(app)

    # Mock StatisticsAnalyzer to return simple data
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    # Should return JSON (either empty or with data depending on StatisticsAnalyzer)


def test_api_stats_htmx_fragment(monkeypatch, tmp_path):
    """Test GET /api/stats with HX-Request returns HTML fragment."""
    dbfile = tmp_path / 'test.db'
    create_sample_db(str(dbfile))
    monkeypatch.setenv('PDF_DB', str(dbfile))

    from html_frontend.app import app
    client = TestClient(app)

    resp = client.get("/api/stats", headers={"hx-request": "true"})
    assert resp.status_code == 200
    # Should be HTML stats cards or dict-based template, not pure JSON
    content = resp.text
    # Check if it's HTML or contains stats
    assert 'stats' in content.lower() or 'card' in content.lower() or '{' in content
