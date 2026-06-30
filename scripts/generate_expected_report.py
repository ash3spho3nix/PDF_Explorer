import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from storage.sqlite import SQLiteDB
from scanner.pipeline import ParallelScanPipeline
from report.markdown import MarkdownReport
from models.scan_context import ScanReport, FolderSummary


def _build_folder_summaries(pdfs, folder_scores):
    folder_summaries = {}
    pdfs_by_folder = {}
    for pdf in pdfs:
        pdfs_by_folder.setdefault(pdf.parent_folder, []).append(pdf)

    for folder, folder_pdfs in pdfs_by_folder.items():
        score_data = folder_scores.get(folder, {})
        category_counts = {}
        for pdf in folder_pdfs:
            category_counts[pdf.category] = category_counts.get(pdf.category, 0) + 1

        folder_summaries[folder] = FolderSummary(
            folder_path=folder,
            total_files=len(folder_pdfs),
            total_size_bytes=sum(pdf.size_bytes for pdf in folder_pdfs),
            category_counts=category_counts,
            folder_score=score_data.get('score', 100.0)
        )

    return folder_summaries


def _build_category_breakdown(stats):
    breakdown = stats.get('category_breakdown', {})
    return {category: values.get('count', 0) for category, values in breakdown.items()}


def _build_findings_strings(findings):
    if not findings:
        return []
    return [f"{item.get('title', 'Finding')} — {item.get('description', '')}" for item in findings]


def main():
    repo_root = Path(__file__).resolve().parent.parent
    fixture_dir = repo_root / 'tests' / 'integration' / 'fixtures' / 'sample_pdfs'
    output_report = repo_root / 'tests' / 'integration' / 'fixtures' / 'expected_report.md'
    db_path = repo_root / 'tests' / 'integration' / 'fixtures' / 'expected_pdf_index.db'
    cache_path = repo_root / 'tests' / 'integration' / 'fixtures' / 'expected_pdf_cache.db'

    pipeline = ParallelScanPipeline(
        max_workers=2,
        batch_size=5,
        cache_path=str(cache_path),
        use_cache=True,
        logger=None
    )
    pipeline.sqlite_db = SQLiteDB(str(db_path))

    result = pipeline.execute(str(fixture_dir))
    total_size_bytes = sum(pdf.size_bytes for pdf in result.pdfs)

    report_data = ScanReport(
        run_id='expected-report',
        start_time=result.start_time,
        end_time=result.end_time,
        total_pdfs=result.total_files,
        total_size_bytes=total_size_bytes,
        pdfs=result.pdfs,
        folder_summaries=_build_folder_summaries(result.pdfs, result.folder_scores),
        global_category_breakdown=_build_category_breakdown(result.stats),
        findings=_build_findings_strings(result.findings)
    )

    report_content = MarkdownReport().generate(report_data)
    output_report.write_text(report_content, encoding='utf-8')
    print(f'Expected report generated at {output_report}')


if __name__ == '__main__':
    main()
