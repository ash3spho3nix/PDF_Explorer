import sqlite3
from pathlib import Path

import pytest
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import letter
from pypdf import PdfReader, PdfWriter

from storage.sqlite import SQLiteDB
from report.markdown import MarkdownReport
from scanner.pipeline import ParallelScanPipeline


def create_pdf(path: Path, title: str, text: str):
    c = Canvas(str(path), pagesize=letter)
    c.setTitle(title)
    c.setAuthor('Test Author')
    c.drawString(72, 720, text)
    c.save()


def create_encrypted_pdf(source: Path, target: Path):
    reader = PdfReader(str(source))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt('secret')
    with open(target, 'wb') as f:
        writer.write(f)


@pytest.fixture(scope='session')
def sample_pdfs(tmp_path_factory):
    root = tmp_path_factory.mktemp('sample_pdfs')
    create_pdf(root / 'invoice_001.pdf', 'Invoice 001', 'Invoice Amount Due: $100')
    create_pdf(root / 'resume_001.pdf', 'Resume 001', 'Experience\nEducation\nSkills Python')
    create_pdf(root / 'dup_a.pdf', 'Duplicate A', 'Duplicate file content')
    create_pdf(root / 'dup_b.pdf', 'Duplicate B', 'Duplicate file content')
    create_pdf(root / 'notes.pdf', 'Notes', 'Some generic note text.')

    corrupted_path = root / 'corrupted.pdf'
    with open(corrupted_path, 'wb') as f:
        f.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\n')

    create_encrypted_pdf(root / 'notes.pdf', root / 'encrypted.pdf')

    return root


def test_full_pipeline_integration(sample_pdfs, tmp_path):
    db_path = tmp_path / 'pdf_index.db'
    cache_path = tmp_path / 'pdf_cache.db'
    report_path = tmp_path / 'pdf_scan_report.md'

    pipeline = ParallelScanPipeline(
        max_workers=2,
        batch_size=5,
        cache_path=str(cache_path),
        use_cache=True,
        logger=None
    )

    # override SQLiteDB path by monkeypatching class attribute if needed
    pipeline.sqlite_db = SQLiteDB(str(db_path))

    result = pipeline.execute(str(sample_pdfs))

    assert result.total_files == 6
    assert result.pdfs
    assert any(pdf.filename == 'invoice_001.pdf' for pdf in result.pdfs)
    assert any(pdf.filename == 'resume_001.pdf' for pdf in result.pdfs)
    assert any('encrypted' in pdf.flags for pdf in result.pdfs)

    report = MarkdownReport().generate(result)
    assert '# 📄 PDF Scan Analytics Execution Report' in report
    assert '## 📂 Category Summary Breakdown' in report
    assert '## 🔍 Noteworthy Analytical Findings' in report
    assert 'Bill' in report or 'CV' in report or 'Unknown' in report

    report_path.write_text(report, encoding='utf-8')

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM pdf_index")
    row = cursor.fetchone()
    conn.close()

    assert row is not None and row[0] == 6
    assert report_path.exists()
