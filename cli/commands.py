"""
Typer command execution layers wire up functional infrastructure processing endpoints.
"""

import time
import uuid
from pathlib import Path
import typer
from models.scan_context import ScanContext, ScanReport, FolderSummary
from config.loader import ConfigLoader
from utils.logging import get_logger
from storage.sqlite import SQLiteDB
from scanner.pipeline import ParallelScanPipeline
from report.markdown import MarkdownReport
from report.console import ConsoleReport

app = typer.Typer(help="CLI Toolkit driving automated document space metric compilation cycles.")
logger = get_logger()


def _build_folder_summaries(pdfs, folder_scores: dict) -> dict:
    """Combines FolderScore.compute() output with raw PDF data into FolderSummary objects."""
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
            total_size_bytes=sum(p.size_bytes for p in folder_pdfs),
            category_counts=category_counts,
            folder_score=score_data.get("score", 100.0)
        )
    return folder_summaries


def _build_category_breakdown(stats: dict) -> dict:
    """Flattens StatisticsAnalyzer's category_breakdown (count+size dicts) into plain counts."""
    breakdown = stats.get("category_breakdown", {})
    return {category: data.get("count", 0) for category, data in breakdown.items()}


def _build_findings_strings(findings: list) -> list:
    """Flattens InterestingFindings' structured dicts into display strings for MarkdownReport."""
    return [f"{f.get('title', 'Finding')} — {f.get('description', '')}" for f in findings]


@app.command("run")
def run_scan(
    target_path: Path = typer.Argument(..., help="Path pointing to target directory containing PDF objects."),
    output_report: Path = typer.Option(Path("pdf_scan_report.md"), "--report", "-r", help="Destination path for generated markdown report.")
):
    """
    Executes a complete read-only scan process, updating caches and generating markdown metrics.
    """
    if not target_path.is_dir():
        typer.secho(f"Error: Target boundary path '{target_path}' is invalid.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    run_id = str(uuid.uuid4())[:8]
    config = ConfigLoader.load_from_path()

    pipeline = ParallelScanPipeline(
        max_workers=config.get("max_workers", 8),
        batch_size=config.get("chunk_size", 100),
        cache_path="pdf_cache.db",
        use_cache=True,
        logger=logger
    )

    try:
        result = pipeline.execute(str(target_path.resolve()))
    except Exception as e:
        typer.secho(f"Error: Scan pipeline failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    folder_summaries = _build_folder_summaries(result.pdfs, result.folder_scores)
    category_breakdown = _build_category_breakdown(result.stats)
    findings_strings = _build_findings_strings(result.findings)
    total_size_bytes = sum(p.size_bytes for p in result.pdfs)

    report_data = ScanReport(
        run_id=run_id,
        start_time=result.start_time,
        end_time=result.end_time,
        total_pdfs=result.total_files,
        total_size_bytes=total_size_bytes,
        pdfs=result.pdfs,
        folder_summaries=folder_summaries,
        global_category_breakdown=category_breakdown,
        findings=findings_strings
    )

    # Save operational pass metrics to db historical trackers
    db = SQLiteDB()
    db.connect()
    db.save_run_metrics(run_id, result.start_time, result.end_time, report_data.total_pdfs, report_data.total_size_bytes)
    db.close()

    # Generate Markdown documentation
    markdown_engine = MarkdownReport()
    report_content = markdown_engine.generate(report_data)
    try:
        output_report.write_text(report_content, encoding="utf-8")
        logger.info(f"[bold green]Report saved successfully to:[/bold green] {output_report}")
    except OSError as e:
        logger.error(f"[bold red]Failed writing report file matrix: {e}[/bold red]")

    # Print terminal readout summaries
    console_engine = ConsoleReport()
    console_engine.display_summary(report_data)
