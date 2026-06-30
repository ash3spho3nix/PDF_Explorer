from pathlib import Path
from scanner.discovery import DirectoryDiscovery


def test_discover_candidates_returns_only_pdf_files(tmp_path):
    root = tmp_path
    (root / "doc.pdf").write_text("pdf content")
    (root / "image.png").write_text("png content")
    (root / "sub").mkdir()
    (root / "sub" / "nested.pdf").write_text("pdf content")

    discoverer = DirectoryDiscovery()
    paths = list(discoverer.discover_candidates(root))

    assert len(paths) == 2
    assert all(path.suffix == ".pdf" for path in paths)


def test_discover_candidates_skips_excluded_directories(tmp_path):
    root = tmp_path
    (root / "keep.pdf").write_text("x")
    exclude = root / "exclude_dir"
    exclude.mkdir()
    (exclude / "skip.pdf").write_text("x")

    discoverer = DirectoryDiscovery(exclude_names={"exclude_dir"})
    paths = list(discoverer.discover_candidates(root))

    assert len(paths) == 1
    assert paths[0].name == "keep.pdf"


def test_discover_candidates_handles_missing_root(tmp_path):
    discoverer = DirectoryDiscovery()
    assert list(discoverer.discover_candidates(tmp_path / "missing")) == []
