import pytest
from pathlib import Path
from scanner.scanner import Scanner
from models.scan_context import ScanContext


def test_scan_returns_pdf_paths(tmp_path):
    root = tmp_path
    (root / "a.pdf").write_text("x")
    (root / "b.txt").write_text("x")

    context = ScanContext(
        root_path=str(root),
        config={"excluded_directories": []},
        sqlite_conn=None,
        stats={"total_pdfs": 0, "total_size_bytes": 0},
        cache={},
        progress=None,
        logger=None,
        start_time=0.0,
    )

    found = Scanner().scan(context)
    assert len(found) == 1
    assert found[0].endswith("a.pdf")
    assert context.stats["total_pdfs"] == 1
    assert context.stats["total_size_bytes"] == (root / "a.pdf").stat().st_size


def test_scan_skips_excluded_directory(tmp_path):
    root = tmp_path
    excluded = root / "skip_dir"
    excluded.mkdir()
    (excluded / "secret.pdf").write_text("x")
    (root / "keep.pdf").write_text("x")

    context = ScanContext(
        root_path=str(root),
        config={"excluded_directories": ["skip_dir"]},
        sqlite_conn=None,
        stats={"total_pdfs": 0, "total_size_bytes": 0},
        cache={},
        progress=None,
        logger=None,
        start_time=0.0,
    )

    found = Scanner().scan(context)
    assert len(found) == 1
    assert found[0].endswith("keep.pdf")
