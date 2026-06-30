"""
Handles transactional storage and persistence routines for tracking scan histories across sessions.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Tuple
from models.pdf_file import PDFFile


class SQLiteDB:
    """Manages transactional state storage using a highly structured SQLite backend schema."""

    def __init__(self, db_path: str = "pdf_inventory.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Establishes an active transactional session with the local storage backend."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._initialize_schema()
        return self.conn

    def close(self):
        """Safely commits changes and terminates active database connections."""
        if self.conn:
            self.conn.commit()
            self.conn.close()
            self.conn = None

    def _initialize_schema(self):
        """Deploys foundational structural tables matching Section 4 requirements."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pdf_index (
                path TEXT PRIMARY KEY,
                filename TEXT,
                parent_folder TEXT,
                size_bytes INTEGER,
                created_time REAL,
                modified_time REAL,
                file_hash TEXT,
                page_count INTEGER,
                category TEXT,
                subcategory TEXT,
                confidence REAL,
                flags TEXT,
                last_scanned REAL
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_runs (
                run_id TEXT PRIMARY KEY,
                start_time REAL,
                end_time REAL,
                total_pdfs INTEGER,
                total_size INTEGER
            );
        """)
        self.conn.commit()

    def insert_pdf(self, pdf: PDFFile):
        """Persists a newly tracked document record inside the data store."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO pdf_index (
                path, filename, parent_folder, size_bytes, created_time, modified_time,
                file_hash, page_count, category, subcategory, confidence, flags, last_scanned
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
        """, (
            pdf.path, pdf.filename, pdf.parent_folder, pdf.size_bytes, pdf.created_time, pdf.modified_time,
            pdf.hash, pdf.page_count, pdf.category, pdf.subcategory, pdf.confidence,
            pdf.to_flags_json()
        ))

    def update_pdf(self, pdf: PDFFile):
        """Updates transactional attributes for an already registered document."""
        self.insert_pdf(pdf)  # INSERT OR REPLACE mirrors update behavior given PRIMARY KEY constraints.

    def get_pdf(self, path: str) -> Optional[PDFFile]:
        """Retrieves an existing file entry from the database by its primary file path key."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM pdf_index WHERE path = ?", (path,))
        row = cursor.fetchone()
        if not row:
            return None
            
        return PDFFile(
            path=row["path"],
            filename=row["filename"],
            parent_folder=row["parent_folder"],
            size_bytes=row["size_bytes"],
            created_time=row["created_time"],
            modified_time=row["modified_time"],
            hash=row["file_hash"],
            page_count=row["page_count"],
            category=row["category"],
            subcategory=row["subcategory"],
            confidence=row["confidence"],
            flags=PDFFile.from_flags_json(row["flags"])
        )

    def save_run_metrics(self, run_id: str, start: float, end: float, total_count: int, total_size: int):
        """Logs historical operational telemetry for administrative auditing dashboards."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO scan_runs (run_id, start_time, end_time, total_pdfs, total_size)
            VALUES (?, ?, ?, ?, ?)
        """, (run_id, start, end, total_count, total_size))
        self.conn.commit()