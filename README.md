---

# 📚 PDF Explorer

> Turn messy folders of PDFs into a structured, searchable knowledge system — locally, privately, and without touching your files.

PDF Explorer scans your document folders and reveals what you actually have: topics, duplicates, hidden clusters, forgotten research threads, and document types — all without requiring any manual tagging or organization.

Think of it as:

> “A local Google for your PDFs — but it understands structure, not just filenames.”

---

## ⚡ What it does

Most people accumulate thousands of PDFs over time — papers, bills, notes, reports — and lose track of them completely.

PDF Explorer fixes that by automatically:

* 🔍 Scanning directories recursively (read-only)
* 🧠 Extracting metadata + first-page text
* 🧾 Classifying documents (e.g. research papers, CVs, books, invoices, tickets)
* 🧬 Detecting duplicates using content hashing
* 🧩 Grouping documents into implicit themes and folders of meaning
* 📊 Generating structured Markdown reports of your library
* 🕰 Tracking how your document collection evolves over time (via SQLite history)

---

## 💡 Why this exists

File systems are blind. Search is shallow. Manual tagging doesn’t scale.

PDF Explorer assumes a simple truth:

> Your documents already contain structure — you just haven’t seen it yet.

---

## 🧪 Example Output

After scanning a folder, you don’t just get a list of files.

You get insights like:

* “You have 37 papers related to battery degradation models, spread across 4 years”
* “12 duplicates found across downloads and research folders”
* “A cluster of CVs and academic applications from 2022–2024”
* “Unexpected theme: repeated interest in FEM stability analysis”

---

## 🧰 Core capabilities

* Fully offline, read-only operation
* Incremental scans (only new/changed files processed)
* SHA256-based duplicate detection
* Lightweight SQLite history tracking
* Markdown report generation for human review

---

## 🚀 Design philosophy

* No file modifications
* No forced organization
* No manual tagging requirement
* Works on messy, real-world folders
* Optimized for insight, not just indexing

---

## 📦 Tech stack

* Python (`pathlib`, `sqlite3`)
* `pypdf` for PDF extraction
* SHA256 hashing for deduplication
* Markdown report generator
* SQLite for scan history

---

## 🧭 Roadmap (early vision)

* Semantic clustering of documents
* Natural language querying over PDF collections
* Integration with local LLMs (Ollama support)
* Google Drive + cloud folder support
* Lightweight web dashboard

---

## 🧠 Status

Early-stage, actively evolving tool for personal knowledge exploration.

---

# 🎯 Demo Flow (this is IMPORTANT for GitHub stars)

Your repo needs a **“wow in 30 seconds” narrative**.

Here’s the ideal demo sequence:

---

## ⚙️ Demo Step 1 — Raw chaos input

User has:

```
/PDFs/
  random/
  downloads/
  research/
  desktop_dump/
```

No organization. Just mess.

---

## ▶️ Run

```bash
pdf-explorer scan ~/PDFs
```

---

## ⚡ Demo Step 2 — Immediate processing

Show terminal output:

```
Scanning 1,842 PDFs...
Extracting metadata...
Detecting duplicates...
Classifying documents...
Building structure...
```

No waiting explanation. Just motion.

---

## 📊 Demo Step 3 — Insight report appears

Show generated markdown:

```
report.md
```

Inside:

### 🔍 Overview

* Total PDFs: 1842
* Unique documents: 1370
* Duplicates found: 472

---

### 🧠 Hidden clusters discovered

#### Cluster: Battery Degradation Research

* 41 documents
* Time range: 2021–2025
* Peak activity: 2023

#### Cluster: FEM Simulation Studies

* 28 documents
* Strong overlap with “mesh stability” keywords

#### Cluster: Financial & Administrative

* 210 documents (mostly invoices/tickets)

---

### ⚠️ Interesting finding

> You have 3 separate collections of identical research papers across different folders.

---

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

## Read-only guarantee

This tool is intentionally read-only. It never writes to PDF files, and all file system activity is limited to scanning, metadata extraction, and read-only hashing. The only writable artifacts are its own SQLite cache and report files.

## Development Status

- Tests: all unit/integration tests currently pass (28 tests).
- Progress UI: a Rich-based progress view is integrated into the `run` command.
- Diagnostics: a `diagnostics` command is available to run a timed scan and emit JSON metrics:

```bash
python main.py diagnostics C:\path\to\pdfs --output diagnostics.json
```

For development notes and a detailed changelog, see `DEV_LOG.md`.
