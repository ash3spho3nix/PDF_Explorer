import os
import sys
import sqlite3
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def create_sample_db(path):
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


def test_list_documents_pagination(monkeypatch, tmp_path):
    """Test server-side SQL pagination in documents adapter."""
    dbfile = tmp_path / 'test_cache.db'
    create_sample_db(str(dbfile))
    monkeypatch.setenv('PDF_DB', str(dbfile))

    from html_frontend.adapters.documents import list_documents

    res = list_documents(page=1, limit=10, q=None)
    assert res['total'] == 2
    assert len(res['items']) == 2
    assert res['page'] == 1
    assert res['limit'] == 10
    filenames = [it['filename'] for it in res['items']]
    assert 'a.pdf' in filenames


def test_list_documents_filter_by_query(monkeypatch, tmp_path):
    """Test query-based filtering (filename/title/author)."""
    dbfile = tmp_path / 'test_cache.db'
    create_sample_db(str(dbfile))
    monkeypatch.setenv('PDF_DB', str(dbfile))

    from html_frontend.adapters.documents import list_documents

    # search for 'Alice' (author of first doc)
    res = list_documents(page=1, limit=10, q='Alice')
    assert res['total'] == 1
    assert len(res['items']) == 1
    assert res['items'][0]['author'] == 'Alice'


def test_list_documents_pagination_offset(monkeypatch, tmp_path):
    """Test pagination with offset (page 2 should be empty for 2 docs)."""
    dbfile = tmp_path / 'test_cache.db'
    create_sample_db(str(dbfile))
    monkeypatch.setenv('PDF_DB', str(dbfile))

    from html_frontend.adapters.documents import list_documents

    # page 2 with limit 2 should be empty (only 2 docs total)
    res = list_documents(page=2, limit=2, q=None)
    assert res['total'] == 2
    assert len(res['items']) == 0
    assert res['page'] == 2
