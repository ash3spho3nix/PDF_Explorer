from analyzer.statistics import StatisticsAnalyzer
from models.pdf_file import PDFFile


def make_pdf(path, category, confidence, page_count, flags=None):
    return PDFFile(
        path=path,
        filename=path.split("/")[-1],
        parent_folder="/tmp/folder",
        size_bytes=1024,
        created_time=1620000000.0,
        modified_time=1620000000.0,
        hash=None,
        page_count=page_count,
        title="Title" if page_count else None,
        author="Author" if page_count else None,
        subject="Subject" if page_count else None,
        keywords="keyword" if page_count else None,
        category=category,
        subcategory=None,
        confidence=confidence,
        flags=flags or [],
    )


def test_compute_returns_empty_stats_for_empty_list():
    stats = StatisticsAnalyzer().compute([])
    assert stats["total_pdfs"] == 0
    assert stats["total_size_bytes"] == 0
    assert stats["total_pages"] == 0
    assert stats["confidence_distribution"] == {}


def test_compute_basic_statistics():
    pdfs = [
        make_pdf("/tmp/a.pdf", "Book", 0.9, 10),
        make_pdf("/tmp/b.pdf", "Research", 0.4, 5),
        make_pdf("/tmp/c.pdf", "Unknown", 0.1, 0),
    ]

    stats = StatisticsAnalyzer().compute(pdfs)

    assert stats["total_pdfs"] == 3
    assert stats["category_breakdown"]["Book"]["count"] == 1
    assert stats["folder_breakdown"]["/tmp/folder"]["count"] == 3
    assert stats["metadata_completeness"]["title"]["present"] == 2
    assert stats["flag_counts"] == {}
    assert stats["confidence_distribution"]["high (>=0.8)"] == 1
    assert stats["confidence_distribution"]["very low (<0.2)"] == 1
