import sys
from pathlib import Path
from typing import Optional

import pytest

# Ensure the repository root is on sys.path so local imports work during tests
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def make_pdffile(
    path: str,
    filename: str = "document.pdf",
    parent_folder: str = "./",
    size_bytes: int = 1024,
    created_time: float = 1620000000.0,
    modified_time: float = 1620000000.0,
    file_hash: Optional[str] = None,
    page_count: Optional[int] = 1,
    title: Optional[str] = "Title",
    author: Optional[str] = "Author",
    subject: Optional[str] = "Subject",
    keywords: Optional[str] = "keyword",
    category: str = "Unknown",
    subcategory: Optional[str] = None,
    confidence: float = 0.0,
    flags: Optional[list[str]] = None,
):
    from models.pdf_file import PDFFile

    return PDFFile(
        path=path,
        filename=filename,
        parent_folder=parent_folder,
        size_bytes=size_bytes,
        created_time=created_time,
        modified_time=modified_time,
        hash=file_hash,
        page_count=page_count,
        title=title,
        author=author,
        subject=subject,
        keywords=keywords,
        category=category,
        subcategory=subcategory,
        confidence=confidence,
        flags=flags or [],
    )


@pytest.fixture
def simple_pdffile():
    return make_pdffile(
        path="/tmp/test.pdf",
        filename="test.pdf",
        parent_folder="/tmp",
        size_bytes=2048,
        created_time=1620000000.0,
        modified_time=1620000000.0,
        file_hash="abc123",
        page_count=2,
        title="Unit Test",
        author="Tester",
        subject="Sample",
        keywords="test",
        category="Book",
        subcategory=None,
        confidence=0.9,
        flags=[],
    )


@pytest.fixture
def corrupted_pdffile():
    return make_pdffile(
        path="/tmp/corrupt.pdf",
        filename="corrupt.pdf",
        parent_folder="/tmp",
        size_bytes=0,
        created_time=1620000000.0,
        modified_time=1620000000.0,
        file_hash=None,
        page_count=None,
        title=None,
        author=None,
        subject=None,
        keywords=None,
        category="Unknown",
        subcategory=None,
        confidence=0.0,
        flags=["corrupted"],
    )


@pytest.fixture
def encrypted_pdffile():
    return make_pdffile(
        path="/tmp/encrypted.pdf",
        filename="encrypted.pdf",
        parent_folder="/tmp",
        size_bytes=1024,
        created_time=1620000000.0,
        modified_time=1620000000.0,
        file_hash=None,
        page_count=0,
        title=None,
        author=None,
        subject=None,
        keywords=None,
        category="Unknown",
        subcategory=None,
        confidence=0.0,
        flags=["encrypted"],
    )
