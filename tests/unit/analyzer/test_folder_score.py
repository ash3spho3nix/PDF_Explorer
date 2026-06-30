from analyzer.folder_score import FolderScore
from models.pdf_file import PDFFile


def make_pdf(path, filename, category, confidence, flags):
    return PDFFile(
        path=path,
        filename=filename,
        parent_folder="/tmp/folder",
        size_bytes=1024,
        created_time=1620000000.0,
        modified_time=1620000000.0,
        hash=None,
        page_count=1,
        title="Title",
        author="Author",
        subject="Subject",
        keywords="keyword",
        category=category,
        subcategory=None,
        confidence=confidence,
        flags=flags,
    )


def test_compute_returns_empty_dict_for_empty_list():
    assert FolderScore().compute([]) == {}


def test_compute_scores_penalties_for_problematic_files():
    files = [
        make_pdf("/tmp/folder/report1.pdf", "report1.pdf", "Unknown", 0.1, []),
        make_pdf("/tmp/folder/duplicate.pdf", "duplicate.pdf", "Book", 0.9, ["duplicate"]),
        make_pdf("/tmp/folder/normal.pdf", "normal.pdf", "Book", 0.9, []),
    ]

    result = FolderScore().compute(files)
    assert "/tmp/folder" in result
    folder_data = result["/tmp/folder"]
    assert folder_data["total"] == 3
    assert folder_data["unknown_count"] == 1
    assert folder_data["duplicate_count"] == 1
    assert folder_data["generic_count"] == 0
    assert 0 <= folder_data["score"] <= 100
    assert "unknown_files" in folder_data["details"]
    assert "duplicate_files" in folder_data["details"]


def test_get_folder_ranking_returns_sorted_results():
    folder_score = FolderScore()
    scores = {
        "/tmp/folder": {"score": 60, "total": 3},
        "/tmp/other": {"score": 90, "total": 1},
    }

    ranking = folder_score.get_folder_ranking(scores)

    assert ranking[0]["folder"] == "/tmp/other"
    assert ranking[1]["folder"] == "/tmp/folder"
