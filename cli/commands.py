"""
Typer command execution layers wire up functional infrastructure processing endpoints.
"""

import time
import uuid
from pathlib import Path
from typing import List
import typer
from models.scan_context import ScanContext, ScanReport, FolderSummary
from config.loader import ConfigLoader
from utils.logging import get_logger
from storage.sqlite import SQLiteDB
from scanner.pipeline import ParallelScanPipeline
from report.markdown import MarkdownReport
from cli.progress import create_pipeline_progress
from report.console import ConsoleReport
import json

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

    # Create and use a Rich progress context for interactive CLI feedback
    with create_pipeline_progress() as progress:
        pipeline = ParallelScanPipeline(
            max_workers=config.get("max_workers", 8),
            batch_size=config.get("chunk_size", 100),
            cache_path="pdf_inventory.db",
            use_cache=True,
            logger=logger,
            progress=progress
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


@app.command("mcp")
def mcp_serve(
    db_path: str = typer.Option("pdf_inventory.db", "--db", help="SQLite DB the MCP bridge reads from."),
):
    """
    Start the MCP bridge server (stdio transport) for LM Studio / Ollama / Claude Desktop.
    Run a scan first to populate the database.
    """
    import os
    os.environ["PDF_BRIDGE_DB_PATH"] = db_path

    try:
        from mcp_bridge.server import main as mcp_main
    except ImportError as e:
        typer.secho(f"Error: MCP dependencies missing — run: pip install mcp\n{e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.secho(f"Starting PDF Explorer MCP bridge (db={db_path})", fg=typer.colors.GREEN)
    mcp_main()


@app.command("watch")
def watch_mode(
    paths: List[Path] = typer.Argument(..., help="One or more directories to watch for PDF changes."),
    db_path: str = typer.Option("pdf_inventory.db", "--db", help="SQLite cache DB to update on changes."),
    debounce: float = typer.Option(2.0, "--debounce", help="Seconds to wait before processing a burst of events."),
    state_dir: str = typer.Option("./watch_state", "--state-dir", help="Directory to persist recovery checkpoints."),
):
    """
    Watch directories for PDF changes and incrementally update the cache.
    Press Ctrl+C to stop.
    """
    from watch.service import WatchService
    from watch.config import WatchConfig

    missing = [str(p) for p in paths if not p.is_dir()]
    if missing:
        typer.secho(f"Error: not a directory: {', '.join(missing)}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    config = WatchConfig(
        directories=[str(p.resolve()) for p in paths],
        cache_path=db_path,
        debounce_delay=debounce,
        state_dir=state_dir,
    )
    typer.secho(f"Watching {len(paths)} director{'y' if len(paths) == 1 else 'ies'}. Ctrl+C to stop.", fg=typer.colors.GREEN)
    WatchService(config).start()


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind the server to."),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on."),
    db_path: str = typer.Option("pdf_inventory.db", "--db", help="SQLite DB path the frontend reads from."),
):
    """
    Launch the HTML frontend (FastAPI + HTMX) to browse the PDF index.
    Run a scan first to populate the database.
    """
    import os
    os.environ["PDF_DB"] = db_path

    try:
        import uvicorn
    except ImportError:
        typer.secho("Error: uvicorn not installed. Run: pip install uvicorn", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.secho(f"Starting PDF Explorer UI at http://{host}:{port}", fg=typer.colors.GREEN)
    uvicorn.run("html_frontend.app:app", host=host, port=port, reload=False)


@app.command("diagnostics")
def diagnostics(
    target_path: Path = typer.Argument(..., help="Path to scan for diagnostics."),
    output: Path = typer.Option(Path("diagnostics.json"), "--output", "-o", help="JSON output file for diagnostics")
):
    """
    Runs a timed scan and emits diagnostics/benchmark metrics as JSON.
    """
    if not target_path.is_dir():
        typer.secho(f"Error: Target path '{target_path}' is invalid.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    config = ConfigLoader.load_from_path()

    # Run pipeline without interactive progress for diagnostics
    pipeline = ParallelScanPipeline(
        max_workers=config.get("max_workers", 8),
        batch_size=config.get("chunk_size", 100),
        cache_path="pdf_inventory.db",
        use_cache=True,
        logger=logger,
        progress=None
    )

    start = time.time()
    try:
        result = pipeline.execute(str(target_path.resolve()))
    except Exception as e:
        typer.secho(f"Error: diagnostics pipeline failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    end = time.time()

    metrics = result.metrics if hasattr(result, 'metrics') else {}
    metrics.update({"diagnostics_run_time": end - start})

    try:
        output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        typer.secho(f"Diagnostics written to {output}", fg=typer.colors.GREEN)
    except OSError as e:
        typer.secho(f"Failed to write diagnostics file: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
