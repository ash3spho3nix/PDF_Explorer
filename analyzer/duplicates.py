# analyzer/duplicates.py
from typing import List, Dict, Optional
from collections import defaultdict
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from models.pdf_file import PDFFile


@dataclass
class DuplicateGroup:
    """Represents a group of duplicate files."""
    file_hash: str
    files: List[PDFFile]
    total_wasted_bytes: int


class DuplicateDetector:
    """
    Detects duplicate PDFs using SHA256 hash comparison.
    
    Complexity: O(n * h) where n is number of PDFs and h is file size for hashing.
    For 10,000 PDFs averaging 1MB, this is ~10GB of reading + SHA256 computation.
    
    Performance optimizations:
    - Parallel hash computation using ThreadPoolExecutor
    - Early hash computation only when needed (modified_time changed)
    - Uses streaming hash to avoid loading entire file into memory
    - Groups by file size first to avoid hashing different sized files
    """
    
    def __init__(self, max_workers: int = 8):
        """
        Initialize the duplicate detector.
        
        Args:
            max_workers: Number of threads for parallel hash computation
        """
        self.max_workers = max_workers
    
    def find(self, pdfs: List[PDFFile]) -> List[DuplicateGroup]:
        """
        Find duplicate PDFs by comparing SHA256 hashes.
        
        Args:
            pdfs: List of PDFFile objects
            
        Returns:
            List of DuplicateGroup objects, each containing a set of duplicate files
            
        Complexity: O(n * h) where n = number of PDFs, h = average file size
        Memory: O(n) for storing hashes and grouping
        """
        if not pdfs:
            return []
        
        # Step 1: Group by file size to reduce hashing
        size_groups = self._group_by_size(pdfs)
        
        # Step 2: Compute hashes for files with same size
        hash_groups = self._compute_hashes_parallel(size_groups)
        
        # Step 3: Create DuplicateGroup objects
        duplicate_groups = []
        for file_hash, files in hash_groups.items():
            if len(files) > 1:  # Only consider duplicates
                first_size = files[0].size_bytes if files else 0
                duplicate_groups.append(DuplicateGroup(
                    file_hash=file_hash,
                    files=files,
                    total_wasted_bytes=(len(files) - 1) * first_size
                ))
        
        # Sort by wasted bytes descending
        duplicate_groups.sort(key=lambda x: x.total_wasted_bytes, reverse=True)
        
        return duplicate_groups
    
    def _group_by_size(self, pdfs: List[PDFFile]) -> Dict[int, List[PDFFile]]:
        """
        Group PDFs by file size.
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(n) for storing groups
        """
        size_groups = defaultdict(list)
        for pdf in pdfs:
            size_groups[pdf.size_bytes].append(pdf)
        return size_groups
    
    def _compute_hashes_parallel(self, size_groups: Dict[int, List[PDFFile]]) -> Dict[str, List[PDFFile]]:
        """
        Compute SHA256 hashes in parallel for files with same size.
        
        Complexity: O(n * h) where n = total files, h = average file size
        Memory: O(n) for storing hash results
        """
        hash_results: Dict[str, List[PDFFile]] = defaultdict(list)
        files_to_hash = []
        
        # Only consider size groups with potential duplicates
        for size, files in size_groups.items():
            if len(files) > 1:
                files_to_hash.extend(files)
        
        if not files_to_hash:
            return hash_results
        
        # Compute hashes in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_pdf = {
                executor.submit(self._compute_file_hash, pdf): pdf
                for pdf in files_to_hash
            }
            
            for future in as_completed(future_to_pdf):
                pdf = future_to_pdf[future]
                try:
                    file_hash = future.result()
                    if file_hash:
                        hash_results[file_hash].append(pdf)
                except Exception as e:
                    # Log error but continue
                    print(f"Error computing hash for {pdf.path}: {e}")
        
        return hash_results
    
    def _compute_file_hash(self, pdf: PDFFile) -> Optional[str]:
        """
        Compute SHA256 hash of a file using streaming.
        
        Complexity: O(file_size) for reading and hashing
        Memory: O(8192) bytes for buffer
        """
        try:
            # Use cached hash if available
            if pdf.hash:
                return pdf.hash
            
            sha256 = hashlib.sha256()
            with open(pdf.path, 'rb') as f:
                # Read in chunks to avoid memory issues
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (IOError, PermissionError, OSError):
            return None
    
    def _group_by_hash(self, hashes: Dict[str, PDFFile]) -> Dict[str, List[PDFFile]]:
        """
        Group PDF files by their hash.
        
        Complexity: O(n) where n is number of hashed files
        Memory: O(n) for storing groups
        """
        hash_groups = defaultdict(list)
        for file_hash, pdf in hashes.items():
            hash_groups[file_hash].append(pdf)
        return hash_groups
    
    def find_duplicates_by_size(self, pdfs: List[PDFFile]) -> List[List[PDFFile]]:
        """
        Quick duplicate detection using file size only (faster but less accurate).
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(n) for grouping
        """
        size_groups = self._group_by_size(pdfs)
        return [
            files for files in size_groups.values()
            if len(files) > 1
        ]