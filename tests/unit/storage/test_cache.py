import json
from pathlib import Path

from storage.cache import CacheManager
from models.pdf_file import PDFFile


def make_pdf(path: str) -> PDFFile:
    return PDFFile(
        path=path,
        filename=Path(path).name,
        parent_folder=str(Path(path).parent),
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


def test_cache_save_load_roundtrip(tmp_path):
    cache_db = tmp_path / "cache.db"
    manager = CacheManager(str(cache_db))

    pdf_path = tmp_path / "file.pdf"
    pdf_path.write_bytes(b"x" * 1024)

    pdf = make_pdf(str(pdf_path))
    pdf.size_bytes = 1024
    pdf.modified_time = pdf_path.stat().st_mtime
    manager.save(pdf)

    assert manager.is_changed(str(pdf_path)) is False
    loaded = manager.load(str(pdf_path))
    assert loaded is not None
    assert loaded.path == str(pdf_path)
    assert loaded.flags == ["new"]


def test_is_changed_detects_missing_file(tmp_path):
    cache_db = tmp_path / "cache.db"
    manager = CacheManager(str(cache_db))
    assert manager.is_changed(str(tmp_path / "missing.pdf")) is True


def test_load_returns_none_for_invalid_json(tmp_path):
    cache_db = tmp_path / "cache.db"
    manager = CacheManager(str(cache_db))
    pdf_path = tmp_path / "file.pdf"
    pdf_path.write_bytes(b"x" * 1024)

    pdf = make_pdf(str(pdf_path))
    pdf.size_bytes = 1024
    pdf.modified_time = pdf_path.stat().st_mtime
    manager.save(pdf)

    # Corrupt the flags JSON directly in SQLite
    with sqlite3.connect(str(cache_db)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pdf_cache SET flags = ? WHERE path = ?",
            ("{invalid_json]", str(pdf_path)),
        )
        conn.commit()

    assert manager.load(str(pdf_path)) is None
