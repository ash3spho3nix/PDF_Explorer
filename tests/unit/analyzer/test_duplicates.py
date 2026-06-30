import hashlib
from pathlib import Path

from analyzer.duplicates import DuplicateDetector
from models.pdf_file import PDFFile


def build_pdf(path: Path, size_bytes: int = 0, category: str = "Unknown", flags=None):
    return PDFFile(
        path=str(path),
        filename=path.name,
        parent_folder=str(path.parent),
        size_bytes=size_bytes or path.stat().st_size,
        created_time=path.stat().st_ctime,
        modified_time=path.stat().st_mtime,
        hash=None,
        page_count=1,
        title="Title",
        author="Author",
        subject="Subject",
        keywords="keyword",
        category=category,
        subcategory=None,
        confidence=0.0,
        flags=flags or [],
    )


def test_find_returns_empty_list_for_no_pdfs():
    assert DuplicateDetector().find([]) == []


def test_find_detects_duplicate_group(tmp_path):
    file_a = tmp_path / "a.pdf"
    file_b = tmp_path / "b.pdf"
    file_a.write_bytes(b"duplicate content")
    file_b.write_bytes(b"duplicate content")

    pdf_a = build_pdf(file_a)
    pdf_b = build_pdf(file_b)

    groups = DuplicateDetector().find([pdf_a, pdf_b])

    assert len(groups) == 1
    duplicate_group = groups[0]
    assert duplicate_group.file_hash is not None
    assert len(duplicate_group.files) == 2
    assert duplicate_group.total_wasted_bytes == pdf_a.size_bytes


def test_find_ignores_files_with_failed_hash(tmp_path, monkeypatch):
    file_a = tmp_path / "a.pdf"
    file_b = tmp_path / "b.pdf"
    file_a.write_bytes(b"content one")
    file_b.write_bytes(b"content two")

    pdf_a = build_pdf(file_a)
    pdf_b = build_pdf(file_b)

    detector = DuplicateDetector()

    def fake_compute_file_hash(pdf):
        if pdf.path == str(file_a):
            return None
        return hashlib.sha256(b"content two").hexdigest()

    monkeypatch.setattr(detector, "_compute_file_hash", fake_compute_file_hash)

    groups = detector.find([pdf_a, pdf_b])
    assert len(groups) == 0


def test_find_handles_hash_collision_with_multiple_files(tmp_path, monkeypatch):
    file_a = tmp_path / "a.pdf"
    file_b = tmp_path / "b.pdf"
    file_c = tmp_path / "c.pdf"
    file_a.write_bytes(b"first")
    file_b.write_bytes(b"second")
    file_c.write_bytes(b"third")

    pdf_a = build_pdf(file_a, size_bytes=5)
    pdf_b = build_pdf(file_b, size_bytes=5)
    pdf_c = build_pdf(file_c, size_bytes=5)

    detector = DuplicateDetector()

    def fake_compute_file_hash(pdf):
        if pdf.path == str(file_a):
            return "collision-hash"
        if pdf.path == str(file_b):
            return "collision-hash"
        return hashlib.sha256(b"third").hexdigest()

    monkeypatch.setattr(detector, "_compute_file_hash", fake_compute_file_hash)

    groups = detector.find([pdf_a, pdf_b, pdf_c])

    assert len(groups) == 1
    assert groups[0].file_hash == "collision-hash"
    assert {p.path for p in groups[0].files} == {str(file_a), str(file_b)}
    assert groups[0].total_wasted_bytes == pdf_a.size_bytes
