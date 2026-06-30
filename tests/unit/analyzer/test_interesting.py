from analyzer.interesting import InterestingFindings
from models.pdf_file import PDFFile


def make_pdf(path, filename, category, flags, title=None, author=None, subject=None, keywords=None):
    return PDFFile(
        path=path,
        filename=filename,
        parent_folder="/tmp/downloads",
        size_bytes=1024,
        created_time=1620000000.0,
        modified_time=1620000000.0,
        hash=None,
        page_count=None,
        title=title,
        author=author,
        subject=subject,
        keywords=keywords,
        category=category,
        subcategory=None,
        confidence=0.5,
        flags=flags,
    )


def test_generate_returns_empty_for_no_pdfs():
    assert InterestingFindings().generate([]) == []


def test_generate_finds_missing_metadata():
    pdf = make_pdf(
        "/tmp/missing.pdf",
        "missing.pdf",
        "Research",
        [],
        title=None,
        author=None,
        subject=None,
        keywords=None,
    )

    findings = InterestingFindings().generate([pdf])
    assert any(f["type"] == "missing_metadata" for f in findings)
    missing_metadata_finding = next(f for f in findings if f["type"] == "missing_metadata")
    assert missing_metadata_finding["files"][0]["filename"] == "missing.pdf"


def test_generate_finds_problematic_files():
    encrypted = make_pdf("/tmp/encrypted.pdf", "encrypted.pdf", "Book", ["encrypted"], title="Title", author="Author", subject="Subject", keywords="k")
    corrupted = make_pdf("/tmp/corrupt.pdf", "corrupt.pdf", "Book", ["corrupted"], title="Title", author="Author", subject="Subject", keywords="k")

    findings = InterestingFindings().generate([encrypted, corrupted])
    problematic = [f for f in findings if f["type"] == "problematic_files"]
    assert problematic
    assert problematic[0]["encrypted"][0]["filename"] == "encrypted.pdf"
    assert problematic[0]["corrupted"][0]["filename"] == "corrupt.pdf"
