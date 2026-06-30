# storage/cache.py
from typing import Optional, Dict, Any
from pathlib import Path
import hashlib
import json
from datetime import datetime
import sqlite3

from models.pdf_file import PDFFile


class CacheManager:
    """
    Manages caching of PDF metadata to avoid redundant processing.
    
    Complexity: O(1) for cache operations (hash lookups)
    Memory: O(n) where n is number of cached entries
    
    Performance optimizations:
    - Uses SQLite for persistent caching
    - Stores both file stats and computed metadata
    - Quick dirty checks using modified_time
    """
    
    def __init__(self, db_path: str = "pdf_cache.db"):
        """
        Initialize the cache manager.
        
        Args:
            db_path: Path to SQLite cache database
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the cache database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pdf_cache (
                    path TEXT PRIMARY KEY,
                    filename TEXT,
                    parent_folder TEXT,
                    size_bytes INTEGER,
                    created_time REAL,
                    modified_time REAL,
                    file_hash TEXT,
                    page_count INTEGER,
                    title TEXT,
                    author TEXT,
                    subject TEXT,
                    keywords TEXT,
                    category TEXT,
                    subcategory TEXT,
                    confidence REAL,
                    flags TEXT,
                    last_cached REAL
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pdf_cache_modified 
                ON pdf_cache(modified_time)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pdf_cache_hash 
                ON pdf_cache(file_hash)
            """)
            conn.commit()
    
    def is_changed(self, pdf_path: str) -> bool:
        """
        Check if a PDF has changed since it was cached.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            True if the file has changed or is not cached, False otherwise
            
        Complexity: O(1) for SQLite lookup
        """
        try:
            # Check if file exists
            path_obj = Path(pdf_path)
            if not path_obj.exists():
                return True
            
            # Get current file stats
            stats = path_obj.stat()
            current_size = stats.st_size
            current_mtime = stats.st_mtime
            
            # Query cache
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT size_bytes, modified_time FROM pdf_cache WHERE path = ?",
                    (pdf_path,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return True  # Not cached
                
                cached_size, cached_mtime = row
                
                # Check if stats match
                if current_size != cached_size or current_mtime != cached_mtime:
                    return True
                
                return False
                
        except (IOError, OSError, sqlite3.Error):
            return True
    
    def load(self, pdf_path: str) -> Optional[PDFFile]:
        """
        Load a PDF from cache if available and unchanged.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            PDFFile object if cached and unchanged, None otherwise
            
        Complexity: O(1) for SQLite lookup
        """
        try:
            # Check if changed first
            if self.is_changed(pdf_path):
                return None
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT path, filename, parent_folder, size_bytes, created_time, modified_time,
                           file_hash, page_count, title, author, subject, keywords,
                           category, subcategory, confidence, flags
                    FROM pdf_cache
                    WHERE path = ?
                    """,
                    (pdf_path,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                # Parse flags from JSON
                flags = json.loads(row[15]) if row[15] else []
                
                # Create PDFFile object
                return PDFFile(
                    path=row[0],
                    filename=row[1],
                    parent_folder=row[2],
                    size_bytes=row[3],
                    created_time=row[4],
                    modified_time=row[5],
                    hash=row[6],
                    page_count=row[7],
                    title=row[8],
                    author=row[9],
                    subject=row[10],
                    keywords=row[11],
                    category=row[12],
                    subcategory=row[13],
                    confidence=row[14],
                    flags=flags
                )
                
        except (sqlite3.Error, json.JSONDecodeError):
            return None
    
    def save(self, pdf: PDFFile):
        """
        Save a PDF to cache.
        
        Args:
            pdf: PDFFile object to cache
            
        Complexity: O(1) for SQLite insert/update
        """
        try:
            # Convert flags to JSON
            flags_json = json.dumps(pdf.flags) if pdf.flags else None
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO pdf_cache (
                        path, filename, parent_folder, size_bytes, created_time, modified_time,
                        file_hash, page_count, title, author, subject, keywords,
                        category, subcategory, confidence, flags, last_cached
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pdf.path,
                        pdf.filename,
                        pdf.parent_folder,
                        pdf.size_bytes,
                        pdf.created_time,
                        pdf.modified_time,
                        pdf.hash,
                        pdf.page_count,
                        pdf.title,
                        pdf.author,
                        pdf.subject,
                        pdf.keywords,
                        pdf.category,
                        pdf.subcategory,
                        pdf.confidence,
                        flags_json,
                        datetime.now().timestamp()
                    )
                )
                conn.commit()
                
        except (sqlite3.Error, json.JSONEncodeError):
            pass
    
    def load_batch(self, pdf_paths: list) -> Dict[str, Optional[PDFFile]]:
        """
        Load multiple PDFs from cache efficiently.
        
        Args:
            pdf_paths: List of PDF file paths
            
        Returns:
            Dictionary mapping file paths to PDFFile objects or None
            
        Complexity: O(n) where n is number of paths
        Memory: O(n) for storing results
        """
        results = {}
        for path in pdf_paths:
            results[path] = self.load(path)
        return results
    
    def clear(self):
        """Clear all cached entries."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM pdf_cache")
                conn.commit()
        except sqlite3.Error:
            pass
    
    def get_cache_size(self) -> int:
        """
        Get number of cached entries.
        
        Returns:
            Number of cached PDFs
            
        Complexity: O(1) for SQLite count
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM pdf_cache")
                return cursor.fetchone()[0]
        except sqlite3.Error:
            return 0
    
    def cleanup_old_entries(self, max_age_days: int = 30):
        """
        Remove cache entries older than max_age_days.
        
        Args:
            max_age_days: Maximum age in days to keep
            
        Complexity: O(n) where n is number of cache entries
        """
        try:
            cutoff = datetime.now().timestamp() - (max_age_days * 24 * 3600)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM pdf_cache WHERE last_cached < ?",
                    (cutoff,)
                )
                conn.commit()
        except sqlite3.Error:
            pass