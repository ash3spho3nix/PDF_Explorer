import sqlite3

from storage.sqlite import SQLiteDB
from models.pdf_file import PDFFile


def make_pdf(path: str) -> PDFFile:
    return PDFFile(
        path=path,
        filename=path.split("/")[-1],
        parent_folder="/tmp",
        size_bytes=1024,
        created_time=1620000000.0,
        modified_time=1620000000.0,
        hash="abc123",
        page_count=1,
        title="Title",
        author="Author",
        subject="Subject",
        keywords="keyword",
        category="Book",
        subcategory=None,
        confidence=0.8,
        flags=["new"],
    )


def test_sqlite_creates_schema_and_persists_pdf(tmp_path):
    db_path = tmp_path / "test.db"
    db = SQLiteDB(str(db_path))
    conn = db.connect()

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pdf_index'")
    assert cursor.fetchone() is not None

    pdf = make_pdf("/tmp/test.pdf")
    db.insert_pdf(pdf)
    fetched = db.get_pdf(pdf.path)

    assert fetched is not None
    assert fetched.path == pdf.path
    assert fetched.filename == pdf.filename
    assert fetched.category == pdf.category
    assert fetched.hash == pdf.hash
    assert fetched.flags == pdf.flags

    db.save_run_metrics("run-1", 1.0, 2.0, 1, 1024)
    cursor.execute("SELECT * FROM scan_runs WHERE run_id = ?", ("run-1",))
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "run-1"

    db.close()


def test_get_pdf_returns_none_when_missing(tmp_path):
    db_path = tmp_path / "missing.db"
    db = SQLiteDB(str(db_path))
    db.connect()
    assert db.get_pdf("/tmp/nonexistent.pdf") is None
    db.close()
