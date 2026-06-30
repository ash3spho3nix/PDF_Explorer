# PDF Explorer

PDF Explorer is a read-only Python tool for scanning directories of PDF files, extracting metadata and first-page text, classifying documents, detecting duplicates, and generating markdown reports. It is designed to be fast, incremental, and human-readable with no file modification.

## What it does

- Discovers PDF files recursively using `pathlib.Path.rglob("*.pdf")`
- Extracts PDF metadata and first-page text with `pypdf`
- Classifies each file into categories like `Bill`, `Ticket`, `CV`, `Thesis`, `Research`, and `Book`
- Detects duplicate files by SHA256 hash for same-size PDFs
- Computes folder scores and interesting findings
- Persists scan history in SQLite and generates a markdown report
- Guarantees read-only operation on scanned PDF files

## Requirements

- Python 3.10+
- `typer`
- `rich`
- `pypdf`

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install typer rich pypdf
```

If this repository later adds a dependency manifest, install from `pyproject.toml` or `requirements.txt`.

## Usage

Run the CLI from the repository root:

```bash
python main.py run C:\path\to\pdfs
```

To generate a markdown report in a custom file:

```bash
python main.py run C:\path\to\pdfs --report my_report.md
```

Available CLI commands:

- `run` — performs a full scan, updates cache, writes markdown report, and prints a terminal summary

## Sample report output

```markdown
# PDF Scan Report

- Total PDFs: 24
- Total Size: 148 MB
- Run Duration: 12.3 seconds

## Folder Summary
- /documents: 12 files, score 88.5
- /downloads: 8 files, score 60.0

## Category Breakdown
- Book: 10
- Research: 5
- Bill: 4

## Findings
- Problematic PDF files — Found 1 encrypted and 0 corrupted files
- Files with missing metadata — Found 2 files with 3+ missing metadata fields
```

## Read-only guarantee

This tool is intentionally read-only. It never writes to PDF files, and all file system activity is limited to scanning, metadata extraction, and read-only hashing. The only writable artifacts are its own SQLite cache and report files.
