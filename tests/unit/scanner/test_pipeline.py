import pytest
from pathlib import Path
from scanner.pipeline import ParallelScanPipeline, ScanResult
from models.scan_context import ScanContext
from storage.cache import CacheManager
from models.pdf_file import PDFFile


class DummyMetadataExtractor:
    def extract_metadata(self, path):
        return {
            "page_count": 1,
            "title": "Title",
            "author": "Author",
            "subject": "Subject",
            "keywords": "keyword",
            "encrypted": False,
        }


class DummyFirstPageExtractor:
    def extract(self, path):
        return "sample text"


@pytest.fixture(autouse=True)
def disable_sqlite(monkeypatch, tmp_path):
    monkeypatch.setattr("scanner.pipeline.SQLiteDB", lambda *args, **kwargs: None)
    return None


def test_execute_returns_empty_result_for_no_pdfs(tmp_path, monkeypatch):
    root = tmp_path
    pipeline = ParallelScanPipeline(use_cache=False)
    pipeline.scanner = type("S", (), {"scan": lambda self, ctx: []})()

    result = pipeline.execute(str(root))
    assert isinstance(result, ScanResult)
    assert result.total_files == 0
    assert result.pdfs == []
    assert result.stats == {}
    assert result.duplicates == []
    assert result.folder_scores == {}
    assert result.findings == []


def test_execute_processes_files_and_uses_cache(tmp_path, monkeypatch):
    root = tmp_path
    pdf_file = root / "doc.pdf"
    pdf_file.write_bytes(b"dummy")

    pipeline = ParallelScanPipeline(use_cache=True, cache_path=str(tmp_path / "cache.db"))
    pipeline.scanner = type("S", (), {"scan": lambda self, ctx: [str(pdf_file)]})()
    pipeline.metadata_extractor = DummyMetadataExtractor()
    pipeline.first_page_extractor = DummyFirstPageExtractor()

    result = pipeline.execute(str(root))
    assert result.total_files == 1
    assert result.failed_files == 0
    assert len(result.pdfs) == 1
    assert result.stats["total_pdfs"] == 1
    assert result.duplicates == []
    assert result.folder_scores
    assert result.findings is not None
