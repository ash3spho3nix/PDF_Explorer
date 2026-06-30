# analyzer/interesting.py
from typing import List, Dict, Tuple, Set
from collections import defaultdict, Counter
import re

from models.pdf_file import PDFFile


class InterestingFindings:
    """
    Generates interesting findings/insights from PDF collection.
    
    Complexity: O(n + c*f + d) where:
        n = number of PDFs
        c = number of categories
        f = number of folders
        d = number of duplicate groups
    
    Memory: O(n + c*f) for storing statistics and findings
    """
    
    def generate(self, pdfs: List[PDFFile]) -> List[Dict[str, any]]:
        """
        Generate interesting findings from the PDF collection.
        
        Args:
            pdfs: List of PDFFile objects
            
        Returns:
            List of finding dictionaries with type, description, and details
            
        Complexity: O(n + c*f) where n = PDFs, c = categories, f = folders
        """
        findings = []
        
        if not pdfs:
            return findings
        
        # 1. Category mismatch in folders
        category_mismatches = self._find_category_mismatches(pdfs)
        if category_mismatches:
            findings.extend(category_mismatches)
        
        # 2. Unusual clustering
        unusual_clusters = self._find_unusual_clustering(pdfs)
        if unusual_clusters:
            findings.extend(unusual_clusters)
        
        # 3. Hidden research papers in downloads
        hidden_research = self._find_hidden_research(pdfs)
        if hidden_research:
            findings.extend(hidden_research)
        
        # 4. Very large files
        large_files = self._find_large_files(pdfs)
        if large_files:
            findings.append(large_files)
        
        # 5. Files with missing metadata
        missing_metadata = self._find_missing_metadata(pdfs)
        if missing_metadata:
            findings.append(missing_metadata)
        
        # 6. Mixed category folders
        mixed_folders = self._find_mixed_category_folders(pdfs)
        if mixed_folders:
            findings.extend(mixed_folders)
        
        # 7. Encrypted or corrupted files
        problematic = self._find_problematic_files(pdfs)
        if problematic:
            findings.append(problematic)
        
        # Sort findings by priority/importance
        findings.sort(key=lambda x: self._get_finding_priority(x['type']), reverse=True)
        
        return findings
    
    def _find_category_mismatches(self, pdfs: List[PDFFile]) -> List[Dict[str, any]]:
        """
        Find files where category doesn't match folder name.
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(n) for storing mismatches
        """
        # Build folder-category mapping
        folder_categories = defaultdict(Counter)
        for pdf in pdfs:
            folder = pdf.parent_folder or "root"
            category = pdf.category or "Unknown"
            folder_categories[folder][category] += 1
        
        # Find mismatches
        findings = []
        for pdf in pdfs:
            folder = pdf.parent_folder or "root"
            category = pdf.category or "Unknown"
            
            # Get dominant category for this folder
            if folder in folder_categories:
                dominant = folder_categories[folder].most_common(1)[0][0]
                if category != dominant and category != "Unknown":
                    findings.append({
                        "type": "category_mismatch",
                        "priority": 7,
                        "title": f"Category mismatch in folder '{folder}'",
                        "description": f"File '{pdf.filename}' is classified as '{category}' but folder mainly contains '{dominant}' files",
                        "file": pdf.filename,
                        "path": pdf.path,
                        "folder": folder,
                        "category": category,
                        "dominant_category": dominant
                    })
        
        # Limit to top findings
        return findings[:20]
    
    def _find_unusual_clustering(self, pdfs: List[PDFFile]) -> List[Dict[str, any]]:
        """
        Find unusual clustering of files (e.g., many PDFs in unexpected locations).
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(f) for folder counts
        """
        findings = []
        
        # Count PDFs per folder
        folder_counts = defaultdict(int)
        for pdf in pdfs:
            folder = pdf.parent_folder or "root"
            folder_counts[folder] += 1
        
        # Find folders with unusually high or low counts
        avg_count = sum(folder_counts.values()) / len(folder_counts) if folder_counts else 0
        
        # Folders with more than 10x average
        for folder, count in folder_counts.items():
            if count > avg_count * 10 and count > 100:
                findings.append({
                    "type": "unusual_cluster",
                    "priority": 6,
                    "title": f"Large PDF cluster in '{folder}'",
                    "description": f"Found {count} PDFs in '{folder}' (average is {avg_count:.1f})",
                    "folder": folder,
                    "count": count,
                    "avg_count": round(avg_count, 1)
                })
        
        return findings
    
    def _find_hidden_research(self, pdfs: List[PDFFile]) -> List[Dict[str, any]]:
        """
        Find research papers hidden in unexpected folders (e.g., Downloads).
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(1)
        """
        hidden_folders = ['downloads', 'download', 'tmp', 'temp', 'desktop']
        research_categories = ['Research', 'Thesis', 'Book']
        
        findings = []
        for pdf in pdfs:
            folder_lower = (pdf.parent_folder or "").lower()
            category = pdf.category or "Unknown"
            
            if category in research_categories:
                # Check if in a hidden/trash folder
                if any(h in folder_lower for h in hidden_folders):
                    findings.append({
                        "type": "hidden_research",
                        "priority": 8,
                        "title": f"Research paper found in '{pdf.parent_folder or 'root'}'",
                        "description": f"'{pdf.filename}' is a {category} paper in a download/temp folder",
                        "file": pdf.filename,
                        "path": pdf.path,
                        "folder": pdf.parent_folder or "root",
                        "category": category,
                        "confidence": pdf.confidence
                    })
        
        return findings[:10]
    
    def _find_large_files(self, pdfs: List[PDFFile]) -> Dict[str, any]:
        """
        Find unusually large PDF files.
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(1)
        """
        if not pdfs:
            return None
        
        # Sort by size descending
        sorted_pdfs = sorted(pdfs, key=lambda x: x.size_bytes, reverse=True)
        
        large_threshold = 50 * 1024 * 1024  # 50MB
        large_files = [p for p in sorted_pdfs if p.size_bytes > large_threshold]
        
        if large_files:
            top_large = large_files[:5]
            return {
                "type": "large_files",
                "priority": 5,
                "title": f"Large PDF files found",
                "description": f"Found {len(large_files)} files larger than 50MB. Top: {', '.join(f['filename'] for f in top_large)}",
                "files": [
                    {
                        "filename": p.filename,
                        "size_mb": round(p.size_bytes / (1024 * 1024), 2),
                        "path": p.path
                    }
                    for p in top_large
                ]
            }
        return None
    
    def _find_missing_metadata(self, pdfs: List[PDFFile]) -> Dict[str, any]:
        """
        Find files with missing metadata.
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(1)
        """
        if not pdfs:
            return None
        
        missing_metadata = []
        for pdf in pdfs:
            metadata_fields = [pdf.title, pdf.author, pdf.subject, pdf.keywords]
            missing = [f for f, v in zip(['title', 'author', 'subject', 'keywords'], metadata_fields) if not v]
            if len(missing) >= 3:
                missing_metadata.append({
                    "filename": pdf.filename,
                    "path": pdf.path,
                    "missing_fields": missing
                })
        
        if missing_metadata:
            return {
                "type": "missing_metadata",
                "priority": 6,
                "title": f"Files with missing metadata",
                "description": f"Found {len(missing_metadata)} files with 3+ missing metadata fields",
                "files": missing_metadata[:10]
            }
        return None
    
    def _find_mixed_category_folders(self, pdfs: List[PDFFile]) -> List[Dict[str, any]]:
        """
        Find folders with mixed categories (low category consistency).
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(f * c) where f = folders, c = categories
        """
        # Group by folder
        folder_categories = defaultdict(Counter)
        for pdf in pdfs:
            folder = pdf.parent_folder or "root"
            category = pdf.category or "Unknown"
            folder_categories[folder][category] += 1
        
        findings = []
        for folder, categories in folder_categories.items():
            total = sum(categories.values())
            if total >= 10:
                dominant, dominant_count = categories.most_common(1)[0]
                consistency = (dominant_count / total) * 100
                if consistency < 60:
                    unique_categories = len(categories)
                    findings.append({
                        "type": "mixed_folder",
                        "priority": 5,
                        "title": f"Mixed category folder: '{folder}'",
                        "description": f"Folder has {unique_categories} categories with only {consistency:.1f}% consistency",
                        "folder": folder,
                        "total_files": total,
                        "categories": dict(categories),
                        "dominant_category": dominant,
                        "consistency": round(consistency, 2)
                    })
        
        return findings[:10]
    
    def _find_problematic_files(self, pdfs: List[PDFFile]) -> Dict[str, any]:
        """
        Find encrypted or corrupted files.
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(1)
        """
        if not pdfs:
            return None
        
        encrypted = [p for p in pdfs if p.flags and "encrypted" in p.flags]
        corrupted = [p for p in pdfs if p.flags and "corrupted" in p.flags]
        
        if encrypted or corrupted:
            return {
                "type": "problematic_files",
                "priority": 9,
                "title": "Problematic PDF files",
                "description": f"Found {len(encrypted)} encrypted and {len(corrupted)} corrupted files",
                "encrypted": [{"filename": p.filename, "path": p.path} for p in encrypted[:5]],
                "corrupted": [{"filename": p.filename, "path": p.path} for p in corrupted[:5]]
            }
        return None
    
    def _get_finding_priority(self, finding_type: str) -> int:
        """
        Get priority score for finding type (higher = more important).
        
        Complexity: O(1)
        """
        priorities = {
            "problematic_files": 9,
            "hidden_research": 8,
            "category_mismatch": 7,
            "missing_metadata": 6,
            "unusual_cluster": 6,
            "large_files": 5,
            "mixed_folder": 5,
            "duplicates": 4
        }
        return priorities.get(finding_type, 3)