DEV LOG — PDF Explorer
======================

Date: 2026-07-01

Overview
--------
This document summarizes development changes applied to the PDF Explorer project during a recent stabilization and observability pass. The goal was to preserve architecture and business logic while fixing test failures, adding deterministic cache behaviour, and improving CLI observability.

High-level status
-----------------
- Test suite: 28 passed (unit and integration tests).
- Progress UI: Rich-based progress integrated into `run` command and pipeline.
- Diagnostics: `diagnostics` CLI command added to produce a JSON metrics file for benchmarking.
- Logging: centralized `utils/logging.py` provides a Rich-enabled logger used across the CLI and pipeline.

Key changes (files modified)
---------------------------
- `scanner/pipeline.py`
  - Introduced `ProcessOutcome` dataclass and `ScanResult` return structure.
  - Parallel batch processing now returns deterministic `(path, ProcessOutcome)` tuples.
  - Progress updates wired into the pipeline (cached/new/changed/failed counters and current file name).
  - Better error handling and metrics collection (timings per stage).

- `storage/cache.py`
  - Deterministic cache status checks via `get_entry_status()` returning `new|changed|cached`.
  - Robust `load()`/`save()` and schema initialization for persistent cache.

- `storage/sqlite.py`
  - Schema initialization aligned with `PDFFile` model fields.
  - `insert_pdf()` and `get_pdf()` handle JSON flags and missing columns safely.
  - Added `save_run_metrics()` to persist scan run telemetry.

- `extractor/metadata.py`
  - Early detection of encrypted PDFs to avoid reading pages for encrypted files.

- `report/markdown.py`
  - Compatibility with `ScanResult` (builds a compatible report context when needed).

- `models/pdf_file.py`
  - Added `classification_explanation` and JSON flags helpers (`to_flags_json()` / `from_flags_json()`).

- `cli/progress.py`
  - Constructed a Rich `Progress` instance with custom columns for cached/new/changed/failed counters and `current_file` display.

- `cli/commands.py`
  - Uses `create_pipeline_progress()` and passes the `progress` instance into `ParallelScanPipeline`.
  - Added `diagnostics` command (timed scan -> writes JSON metrics).

- `utils/logging.py`
  - Centralized logger factory using Rich for readable terminal logs.

Why these changes
-----------------
- Tests failed due to schema/typing mismatches, pipeline return shapes, and encrypted PDF handling. Fixing these at the source preserved the overall architecture while making behavior deterministic.
- Adding deterministic cache status methods allowed the pipeline to report accurate counters in the progress UI.
- The `diagnostics` command produces reproducible metrics for benchmarking and troubleshooting without interactive UI dependencies.

How to run
----------
- Run full CLI scan (interactive progress):

```bash
python main.py run C:\path\to\pdfs --report my_report.md
```

- Run diagnostics (timed metrics written as JSON):

```bash
python main.py diagnostics C:\path\to\pdfs --output diagnostics.json
```

- Run tests (project root):

```bash
pytest -q
```

Notes & next steps
------------------
- Logging instrumentation is in place; more structured (JSON) log output or an audit sink can be added if desired.
- A benchmark mode (multi-run, statistical summary) could be added to `diagnostics` to collect aggregated throughput numbers.
- Consider exposing a `--json` flag for commands that currently print human-friendly output so CI systems can parse results.

Contact
-------
For follow-ups, update this file with additional context or open an issue describing the desired next diagnostic or benchmark behaviour.
