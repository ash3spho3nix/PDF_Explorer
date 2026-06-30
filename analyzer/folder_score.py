# analyzer/folder_score.py
from typing import Dict, List, Optional, Set
from collections import defaultdict
import re

from models.pdf_file import PDFFile


class FolderScore:
    """
    Computes quality scores for folders based on various metrics.
    
    Score Formula:
        100 - unknown_penalty - duplicate_penalty - generic_filename_penalty
        
    Where penalties are scaled to keep score between 0 and 100.
    
    Complexity: O(n + f) where n = number of PDFs, f = number of folders
    Memory: O(f + total_pdfs) for storing folder statistics
    """
    
    def __init__(self, max_workers: int = 8):
        """
        Initialize the folder scorer.
        
        Args:
            max_workers: Number of threads for parallel processing
        """
        self.max_workers = max_workers
        
        # Patterns for generic filenames
        self.generic_patterns = [
            re.compile(r'^document\d*\.pdf$', re.IGNORECASE),
            re.compile(r'^file\d*\.pdf$', re.IGNORECASE),
            re.compile(r'^pdf\d*\.pdf$', re.IGNORECASE),
            re.compile(r'^untitled\d*\.pdf$', re.IGNORECASE),
            re.compile(r'^new\d*\.pdf$', re.IGNORECASE),
            re.compile(r'^scan\d*\.pdf$', re.IGNORECASE),
            re.compile(r'^image\d*\.pdf$', re.IGNORECASE),
        ]
    
    def compute(self, pdfs: List[PDFFile]) -> Dict[str, Dict[str, any]]:
        """
        Compute folder scores for all folders.
        
        Args:
            pdfs: List of PDFFile objects
            
        Returns:
            Dictionary mapping folder names to score information
            
        Complexity: O(n + f) where n = number of PDFs, f = number of folders
        Memory: O(f + total_pdfs) for storing folder statistics
        """
        if not pdfs:
            return {}
        
        # Group PDFs by folder
        folder_groups = self._group_by_folder(pdfs)
        
        folder_scores = {}
        for folder, folder_pdfs in folder_groups.items():
            folder_scores[folder] = self._score_folder(folder, folder_pdfs)
        
        # Sort by score descending
        return dict(sorted(
            folder_scores.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        ))
    
    def _group_by_folder(self, pdfs: List[PDFFile]) -> Dict[str, List[PDFFile]]:
        """
        Group PDFs by parent folder.
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(f + n) for storing groups
        """
        folder_groups = defaultdict(list)
        for pdf in pdfs:
            folder = pdf.parent_folder or "root"
            folder_groups[folder].append(pdf)
        return folder_groups
    
    def _score_folder(self, folder: str, pdfs: List[PDFFile]) -> Dict[str, any]:
        """
        Compute score for a single folder.
        
        Args:
            folder: Folder name
            pdfs: List of PDFs in the folder
            
        Returns:
            Dictionary with score and detailed metrics
            
        Complexity: O(n) where n is number of PDFs in the folder
        Memory: O(1)
        """
        total = len(pdfs)
        if total == 0:
            return {
                "score": 0,
                "total": 0,
                "unknown_count": 0,
                "duplicate_count": 0,
                "generic_count": 0,
                "details": {}
            }
        
        # Count problematic files
        unknown_count = 0
        duplicate_count = 0
        generic_count = 0
        
        # Track duplicate groups within folder
        duplicate_hashes = set()
        duplicate_files = set()
        
        # Track generic filenames
        for pdf in pdfs:
            # Check for Unknown category
            if pdf.category == "Unknown" or (pdf.confidence is not None and pdf.confidence < 0.4):
                unknown_count += 1
            
            # Check for duplicate flags
            if pdf.flags and "duplicate" in pdf.flags:
                duplicate_count += 1
                duplicate_files.add(pdf.path)
            
            # Check for generic filename
            if self._is_generic_filename(pdf.filename):
                generic_count += 1
        
        # Calculate penalties (capped at 100 total)
        unknown_penalty = min(50, (unknown_count / total) * 50)
        duplicate_penalty = min(30, (duplicate_count / total) * 30)
        generic_penalty = min(20, (generic_count / total) * 20)
        
        # Base score
        score = max(0, 100 - unknown_penalty - duplicate_penalty - generic_penalty)
        
        return {
            "score": round(score, 2),
            "total": total,
            "unknown_count": unknown_count,
            "unknown_percentage": round((unknown_count / total) * 100, 2),
            "duplicate_count": duplicate_count,
            "duplicate_percentage": round((duplicate_count / total) * 100, 2),
            "generic_count": generic_count,
            "generic_percentage": round((generic_count / total) * 100, 2),
            "penalties": {
                "unknown": round(unknown_penalty, 2),
                "duplicate": round(duplicate_penalty, 2),
                "generic": round(generic_penalty, 2)
            },
            "details": {
                "unknown_files": [p.filename for p in pdfs if p.category == "Unknown" or (p.confidence is not None and p.confidence < 0.4)],
                "duplicate_files": [p.filename for p in pdfs if p.flags and "duplicate" in p.flags],
                "generic_files": [p.filename for p in pdfs if self._is_generic_filename(p.filename)]
            }
        }
    
    def _is_generic_filename(self, filename: str) -> bool:
        """
        Check if a filename is generic/meaningless.
        
        Complexity: O(p) where p is number of generic patterns (7)
        Memory: O(1)
        """
        if not filename:
            return True
        
        # Check against patterns
        for pattern in self.generic_patterns:
            if pattern.match(filename):
                return True
        
        # Check for very short names (less than 5 chars without extension)
        name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
        if len(name_without_ext) < 5:
            return True
        
        return False
    
    def get_folder_ranking(self, folder_scores: Dict[str, Dict[str, any]]) -> List[Dict[str, any]]:
        """
        Get ranking of folders by score.
        
        Args:
            folder_scores: Output from compute() method
            
        Returns:
            List of folder rankings with scores and metrics
            
        Complexity: O(f log f) where f is number of folders
        Memory: O(f) for storing ranking
        """
        ranking = []
        for folder, data in folder_scores.items():
            ranking.append({
                "folder": folder,
                "score": data["score"],
                "total": data["total"],
                "health": self._get_health_status(data["score"])
            })
        
        return sorted(ranking, key=lambda x: x["score"], reverse=True)
    
    def _get_health_status(self, score: float) -> str:
        """
        Get health status based on score.
        
        Complexity: O(1)
        """
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "fair"
        elif score >= 20:
            return "poor"
        else:
            return "critical"