# analyzer/statistics.py
from typing import List, Dict, Optional
from collections import defaultdict
from datetime import datetime
import math

from models.pdf_file import PDFFile
from intelligence import IAMProcessor, IAMConfig

class StatisticsAnalyzer:
    """
    Computes comprehensive statistics for a collection of PDF files.
    
    Complexity: O(n) where n is number of PDFs
    Memory: O(c + f) where c = number of categories, f = number of folders
    """
    
    def compute(self, pdfs: List[PDFFile]) -> Dict[str, any]:
        """
        Compute comprehensive statistics for the given PDFs.
        
        Args:
            pdfs: List of PDFFile objects
            
        Returns:
            Dictionary containing various statistics
            
        Complexity: O(n) for iterating through all PDFs
        Memory: O(c + f) where c = categories, f = folders
        """
        if not pdfs:
            return self._empty_stats()
        
        stats = {
            # Overall counts
            "total_pdfs": len(pdfs),
            "total_size_bytes": sum(p.size_bytes for p in pdfs),
            "total_size_mb": round(sum(p.size_bytes for p in pdfs) / (1024 * 1024), 2),
            
            # Category breakdown
            "category_breakdown": self._compute_category_breakdown(pdfs),
            
            # Folder breakdown
            "folder_breakdown": self._compute_folder_breakdown(pdfs),
            
            # File statistics
            "avg_file_size_mb": round(sum(p.size_bytes for p in pdfs) / len(pdfs) / (1024 * 1024), 2),
            "median_file_size_mb": self._compute_median_size(pdfs),
            "max_file_size_mb": round(max(p.size_bytes for p in pdfs) / (1024 * 1024), 2),
            "min_file_size_mb": round(min(p.size_bytes for p in pdfs) / (1024 * 1024), 2),
            
            # Page statistics
            "total_pages": sum(p.page_count or 0 for p in pdfs),
            "avg_pages": round(sum(p.page_count or 0 for p in pdfs) / len(pdfs), 2) if pdfs else 0,
            
            # Time statistics
            "oldest_file": min(p.modified_time for p in pdfs),
            "newest_file": max(p.modified_time for p in pdfs),
            "file_age_days": self._compute_age_stats(pdfs),
            
            # Metadata completeness
            "metadata_completeness": self._compute_metadata_completeness(pdfs),
            
            # Quality metrics
            "confidence_distribution": self._compute_confidence_distribution(pdfs),
            "flag_counts": self._compute_flag_counts(pdfs),
            
            # Category consistency
            "category_folder_consistency": self._compute_category_consistency(pdfs),
        }
        
        return stats
    
    def _empty_stats(self) -> Dict[str, any]:
        """Return empty statistics for empty input."""
        return {
            "total_pdfs": 0,
            "total_size_bytes": 0,
            "total_size_mb": 0,
            "category_breakdown": {},
            "folder_breakdown": {},
            "avg_file_size_mb": 0,
            "median_file_size_mb": 0,
            "max_file_size_mb": 0,
            "min_file_size_mb": 0,
            "total_pages": 0,
            "avg_pages": 0,
            "oldest_file": 0,
            "newest_file": 0,
            "file_age_days": {"avg": 0, "min": 0, "max": 0},
            "metadata_completeness": {},
            "confidence_distribution": {},
            "flag_counts": {},
            "category_folder_consistency": {},
        }
    
    def _compute_category_breakdown(self, pdfs: List[PDFFile]) -> Dict[str, Dict[str, any]]:
        """
        Compute category breakdown with counts and sizes.
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(c) where c is number of categories
        """
        breakdown = defaultdict(lambda: {"count": 0, "size_bytes": 0})
        
        for pdf in pdfs:
            category = pdf.category or "Unknown"
            breakdown[category]["count"] += 1
            breakdown[category]["size_bytes"] += pdf.size_bytes
        
        # Calculate percentages and convert to dict
        total = len(pdfs)
        result = {}
        for category, data in breakdown.items():
            data["percentage"] = round((data["count"] / total) * 100, 2) if total > 0 else 0
            data["size_mb"] = round(data["size_bytes"] / (1024 * 1024), 2)
            data["avg_size_mb"] = round(data["size_bytes"] / data["count"] / (1024 * 1024), 2)
            result[category] = data
        
        return result
    
    def _compute_folder_breakdown(self, pdfs: List[PDFFile]) -> Dict[str, Dict[str, any]]:
        """
        Compute folder breakdown with counts and sizes.
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(f) where f is number of folders
        """
        breakdown = defaultdict(lambda: {"count": 0, "size_bytes": 0})
        
        for pdf in pdfs:
            folder = pdf.parent_folder or "root"
            breakdown[folder]["count"] += 1
            breakdown[folder]["size_bytes"] += pdf.size_bytes
        
        # Convert to dict and calculate metrics
        result = {}
        for folder, data in breakdown.items():
            data["size_mb"] = round(data["size_bytes"] / (1024 * 1024), 2)
            result[folder] = data
        
        return result
    
    def _compute_median_size(self, pdfs: List[PDFFile]) -> float:
        """
        Compute median file size in MB.
        
        Complexity: O(n log n) for sorting
        Memory: O(n) for storing sizes
        """
        if not pdfs:
            return 0.0
        
        sizes = sorted(p.size_bytes for p in pdfs)
        mid = len(sizes) // 2
        
        if len(sizes) % 2 == 0:
            median = (sizes[mid - 1] + sizes[mid]) / 2
        else:
            median = sizes[mid]
        
        return round(median / (1024 * 1024), 2)
    
    def _compute_age_stats(self, pdfs: List[PDFFile]) -> Dict[str, any]:
        """
        Compute file age statistics in days.
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(1)
        """
        if not pdfs:
            return {"avg": 0, "min": 0, "max": 0}
        
        now = datetime.now().timestamp()
        ages = [(now - p.modified_time) / (24 * 3600) for p in pdfs]
        
        return {
            "avg": round(sum(ages) / len(ages), 2),
            "min": round(min(ages), 2),
            "max": round(max(ages), 2)
        }
    
    def _compute_metadata_completeness(self, pdfs: List[PDFFile]) -> Dict[str, any]:
        """
        Compute metadata completeness statistics.
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(1)
        """
        fields = ['title', 'author', 'subject', 'keywords', 'page_count']
        completeness = {}
        
        for field in fields:
            count = sum(1 for p in pdfs if getattr(p, field, None))
            completeness[field] = {
                "present": count,
                "missing": len(pdfs) - count,
                "percentage": round((count / len(pdfs)) * 100, 2) if pdfs else 0
            }
        
        return completeness
    
    def _compute_confidence_distribution(self, pdfs: List[PDFFile]) -> Dict[str, int]:
        """
        Compute distribution of confidence scores.
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(1)
        """
        distribution = {
            "high (>=0.8)": 0,
            "medium (0.5-0.8)": 0,
            "low (0.2-0.5)": 0,
            "very low (<0.2)": 0
        }
        
        for pdf in pdfs:
            confidence = pdf.confidence or 0.0
            if confidence >= 0.8:
                distribution["high (>=0.8)"] += 1
            elif confidence >= 0.5:
                distribution["medium (0.5-0.8)"] += 1
            elif confidence >= 0.2:
                distribution["low (0.2-0.5)"] += 1
            else:
                distribution["very low (<0.2)"] += 1
        
        return distribution
    
    def _compute_flag_counts(self, pdfs: List[PDFFile]) -> Dict[str, int]:
        """
        Count occurrences of each flag.
        
        Complexity: O(n * f) where n = number of PDFs, f = average flags per PDF
        Memory: O(f) where f is number of unique flags
        """
        flag_counts = defaultdict(int)
        for pdf in pdfs:
            for flag in pdf.flags or []:
                flag_counts[flag] += 1
        return dict(flag_counts)
    
    def _compute_category_consistency(self, pdfs: List[PDFFile]) -> Dict[str, any]:
        """
        Compute consistency between category and folder.
        
        Complexity: O(n) where n is number of PDFs
        Memory: O(c * f) where c = categories, f = folders
        """
        folder_categories = defaultdict(lambda: defaultdict(int))
        
        for pdf in pdfs:
            folder = pdf.parent_folder or "root"
            category = pdf.category or "Unknown"
            folder_categories[folder][category] += 1
        
        consistency = {}
        for folder, categories in folder_categories.items():
            total = sum(categories.values())
            if total > 0:
                main_category = max(categories, key=categories.get)
                consistency[folder] = {
                    "total_files": total,
                    "main_category": main_category,
                    "main_category_percentage": round((categories[main_category] / total) * 100, 2),
                    "category_distribution": dict(categories)
                }
        
        return consistency
        
    def analyze_with_intelligence(self, pdfs, config_path=None):
        """Optional hook to run IAM."""
        if config_path:
            import yaml
            with open(config_path) as f:
                cfg_dict = yaml.safe_load(f)
                iam_config = IAMConfig(**cfg_dict.get("iam", {}))
        else:
            iam_config = IAMConfig()

        if iam_config.enabled:
            processor = IAMProcessor(self.db_path, iam_config)
            results = processor.analyze(pdfs)
            # Store results in self.iam_results for report generator
            self.iam_results = results
            return results
        return {}    