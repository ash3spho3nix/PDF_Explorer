# 📄 PDF Inventory CLI (v1.0) — Final Technical Design

---

# 1. Core Philosophy (Immutable)

This system is:

* Read-only (never modifies files)
* Fast-first (avoid PDF parsing unless necessary)
* Incremental (cache everything possible)
* Weekly-run oriented (diff over time)
* Human-readable (reports > logs)
* Modular (each module independently testable)

---

# 2. Tech Stack (STRICT)

## Python Version

* Python **3.10+**

---

## Core Libraries

### Filesystem + System

* `pathlib` (preferred over os.path)
* `os`
* `hashlib`
* `time`
* `datetime`

---

### PDF Handling (minimal footprint)

* `pypdf` → metadata + page count + first page text

  * (NOT PyPDF2 — use maintained fork)
* optional fallback:

  * `pdfminer.six` → only if pypdf fails

---

### CLI

* `typer` → CLI framework (clean + modern)
* `rich` → progress bars + console UI

---

### Performance

* `concurrent.futures` → multiprocessing/threading
* `threading` → lightweight coordination

---

### Storage

* `sqlite3` (built-in)

---

### Utilities

* `dataclasses`
* `enum`
* `typing`
* `json`

---

### Optional (no LLM in v1)

* NONE

---

# 3. Data Model (CORE CONTRACT)

## models/pdf_file.py

```python
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class PDFFile:
    path: str
    filename: str
    parent_folder: str

    size_bytes: int

    created_time: float
    modified_time: float

    hash: Optional[str]

    page_count: Optional[int]

    title: Optional[str]
    author: Optional[str]
    subject: Optional[str]
    keywords: Optional[str]

    category: str
    subcategory: Optional[str]
    confidence: float

    flags: List[str]
```

---

## Flags Enum

```python
class PDFFlags:
    DUPLICATE = "duplicate"
    GENERIC_NAME = "generic_name"
    UNKNOWN = "unknown"
    ENCRYPTED = "encrypted"
    CORRUPTED = "corrupted"
    NEW = "new"
```

---

# 4. SQLite Schema

## storage/sqlite.py

### Table: pdf_index

```sql
CREATE TABLE pdf_index (
    path TEXT PRIMARY KEY,
    filename TEXT,
    parent_folder TEXT,

    size_bytes INTEGER,
    modified_time REAL,

    file_hash TEXT,

    page_count INTEGER,

    category TEXT,
    subcategory TEXT,
    confidence REAL,

    flags TEXT, -- JSON list

    last_scanned REAL
);
```

---

### Table: scan_runs

```sql
CREATE TABLE scan_runs (
    run_id TEXT PRIMARY KEY,
    start_time REAL,
    end_time REAL,
    total_pdfs INTEGER,
    total_size INTEGER
);
```

---

# 5. Scan Context (GLOBAL STATE OBJECT)

## models/scan_context.py

```python
@dataclass
class ScanContext:
    root_path: str
    config: dict

    sqlite_conn: any

    stats: dict
    cache: dict

    progress: any  # rich progress bar
    logger: any

    start_time: float
```

---

# 6. Scanner Module

## scanner/scanner.py

### Class: Scanner

```python
class Scanner:
    def scan(self, context: ScanContext) -> List[str]:
        """
        Returns list of PDF file paths
        """
```

### Method behavior:

* Uses `pathlib.Path.rglob("*.pdf")`
* Filters:

  * broken links
  * permission errors
* returns raw file list

---

# 7. Extractor Module

## extractor/metadata.py

```python
class MetadataExtractor:
    def extract_metadata(self, pdf_path: str) -> dict:
```

### Uses:

* `pypdf.PdfReader`

### Output:

```python
{
    "page_count": int,
    "title": str,
    "author": str,
    "subject": str,
    "keywords": str,
    "encrypted": bool
}
```

---

## extractor/first_page.py

```python
class FirstPageExtractor:
    def extract(self, pdf_path: str) -> str:
```

* Reads only page 1
* fallback: empty string

---

# 8. Classifier Module

## classifier/rules.py

### Class: RuleClassifier

```python
class RuleClassifier:
    def classify(self, pdf: PDFFile, text: str) -> tuple[str, float, dict]:
```

### Logic order:

1. Filename rules
2. Metadata rules
3. First page keywords

### Output:

```python
(category, confidence, debug_info)
```

---

## Classification rules (hardcoded)

| Category | Keywords                    |
| -------- | --------------------------- |
| Bill     | invoice, gst, total, amount |
| Ticket   | boarding, flight, seat      |
| CV       | resume, skills, experience  |
| Thesis   | dissertation, university    |
| Research | abstract, doi, ieee         |
| Book     | chapter, table of contents  |

---

# 9. Analyzer Module

---

## statistics.py

```python
class StatisticsAnalyzer:
    def compute(self, pdfs: List[PDFFile]) -> dict:
```

Outputs:

* total PDFs
* total size
* category breakdown
* folder breakdown

---

## duplicates.py

```python
class DuplicateDetector:
    def find(self, pdfs: List[PDFFile]) -> List[List[PDFFile]]:
```

Method:

* SHA256 hash comparison

---

## folder_score.py

```python
class FolderScore:
    def compute(self, folder_stats: dict) -> dict:
```

Score formula:

```text
100
- unknown_penalty
- duplicate_penalty
- generic_filename_penalty
```

---

## unknown.py

```python
class UnknownAnalyzer:
    def find(self, pdfs: List[PDFFile]) -> List[PDFFile]:
```

Criteria:

* low confidence (<0.4)
* missing metadata
* rule failure

---

## interesting.py

```python
class InterestingFindings:
    def generate(self, pdfs: List[PDFFile]) -> List[str]:
```

Rules:

* category mismatch in folders
* unusual clustering
* hidden research papers in downloads

---

# 10. Storage Module

## storage/cache.py

```python
class CacheManager:
    def is_changed(self, pdf_path: str) -> bool:
    def load(self, pdf_path: str) -> Optional[PDFFile]:
    def save(self, pdf: PDFFile):
```

Logic:

* compare modified_time + hash

---

## storage/sqlite.py

```python
class SQLiteDB:
    def connect(self)
    def insert_pdf(self, pdf: PDFFile)
    def get_pdf(self, path: str)
    def update_pdf(self, pdf: PDFFile)
```

---

# 11. Report Module

## report/markdown.py

```python
class MarkdownReport:
    def generate(self, context: ScanContext, data: dict) -> str:
```

Sections:

* Overview
* Category Summary
* Folder Summary
* Storage Summary
* Statistics
* Findings
* Unknown PDFs
* Duplicates
* Generic filenames
* New PDFs
* Folder Scores
* Weekly Summary

---

## report/console.py

Uses `rich`

* progress bar
* live folder updates
* current file display

---

# 12. CLI Module

## cli/commands.py

Using `typer`

### Commands:

```bash
pdfscan run <path>
pdfscan report <path>
pdfscan summary <path>
```

---

## CLI behavior

* starts scan
* shows live progress
* writes markdown report
* optional console summary

---

# 13. Progress System

## cli/progress.py

Uses `rich.progress`

Tracks:

* files scanned
* folders scanned
* current file
* category detection status

---

# 14. Scan Pipeline (FINAL FLOW)

```text
CLI Entry
   ↓
Scanner
   ↓
Cache Check
   ↓
Extractor
   ↓
Classifier
   ↓
Analyzer
   ↓
Storage Update
   ↓
Report Generator
```

---

# 15. Performance Strategy

## Rules:

* NEVER open full PDF unless required
* Use metadata first
* Only first page text
* Cache aggressively
* Parallel scan using ThreadPoolExecutor

---

# 16. Parallel Execution

```python
ThreadPoolExecutor(max_workers=8)
```

Tasks:

* metadata extraction
* hash computation
* classification

---
