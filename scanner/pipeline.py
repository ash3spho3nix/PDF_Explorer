# scanner/pipeline.py
from typing import List, Optional, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime
import time
import logging
from dataclasses import dataclass

from models.pdf_file import PDFFile
from models.scan_context import ScanContext
from storage.cache import CacheManager
from scanner.scanner import Scanner
from extractor.metadata import MetadataExtractor
from extractor.first_page import FirstPageExtractor
from classifier.rules import RuleClassifier
from analyzer.statistics import StatisticsAnalyzer
from analyzer.duplicates import DuplicateDetector
from analyzer.folder_score import FolderScore
from analyzer.interesting import InterestingFindings
from storage.sqlite import SQLiteDB


@dataclass
class ScanResult:
    """Results from a scan pipeline execution."""
    total_files: int
    new_files: int
    changed_files: int
    cached_files: int
    failed_files: int
    start_time: float
    end_time: float
    duration_seconds: float
    pdfs: List[PDFFile]
    stats: Dict[str, Any]
    duplicates: List[Any]
    folder_scores: Dict[str, Any]
    findings: List[Dict[str, Any]]


class ParallelScanPipeline:
    """
    Implements the parallel scan pipeline for processing PDFs efficiently.
    
    Pipeline Stages:
        1. Scanner - Discover PDF files
        2. Cache Check - Identify changed files
        3. Extractor - Extract metadata and first page text
        4. Classifier - Classify each PDF
        5. Analyzer - Compute statistics, duplicates, etc.
        6. Storage - Save results to SQLite
        7. Report - Generate findings
    
    Complexity: O(n * (c + e + cl)) where:
        n = number of PDFs
        c = cache check cost
        e = extraction cost (metadata + first page)
        cl = classification cost
        
    With 10,000 PDFs, this should process in under 10 minutes with 8 workers.
    
    Performance optimizations:
    - Parallel processing using ThreadPoolExecutor
    - Batch processing to avoid memory issues
    - Aggressive caching to avoid reprocessing
    - Streaming results to minimize memory usage
    """
    
    def __init__(
        self,
        max_workers: int = 8,
        batch_size: int = 100,
        cache_path: str = "pdf_cache.db",
        use_cache: bool = True,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the scan pipeline.
        
        Args:
            max_workers: Maximum number of parallel threads
            batch_size: Number of files to process in each batch
            cache_path: Path to cache database
            use_cache: Whether to use caching
            logger: Logger instance for logging
        """
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.use_cache = use_cache
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize components
        self.cache_manager = CacheManager(cache_path) if use_cache else None
        self.scanner = Scanner()
        self.metadata_extractor = MetadataExtractor()
        self.first_page_extractor = FirstPageExtractor()
        self.classifier = RuleClassifier()
        self.statistics_analyzer = StatisticsAnalyzer()
        self.duplicate_detector = DuplicateDetector(max_workers)
        self.folder_scorer = FolderScore(max_workers)
        self.interesting_finder = InterestingFindings()
        self.sqlite_db = SQLiteDB()  # Assuming SQLiteDB exists
    
    def execute(self, root_path: str) -> ScanResult:
        """
        Execute the complete scan pipeline.
        
        Args:
            root_path: Root directory to scan
            
        Returns:
            ScanResult containing all scan data
            
        Complexity: O(n * (c + e + cl)) where n = number of PDFs
        """
        start_time = time.time()
        self.logger.info(f"Starting scan pipeline for {root_path}")
        
        try:
            # Step 1: Scanner - Discover PDF files
            self.logger.info("Step 1: Discovering PDF files...")
            pdf_paths = self._discover_pdfs(root_path)
            total_files = len(pdf_paths)
            self.logger.info(f"Found {total_files} PDF files")
            
            if not pdf_paths:
                self.logger.warning("No PDF files found")
                return self._create_empty_result(start_time)
            
            # Step 2: Process files in parallel
            self.logger.info(f"Step 2: Processing files with {self.max_workers} workers...")
            processed_pdfs, new_count, changed_count, cached_count, failed_count = self._process_files_parallel(pdf_paths)
            
            # Step 3: Analyze results
            self.logger.info("Step 3: Analyzing results...")
            stats = self._analyze_statistics(processed_pdfs)
            duplicates = self._find_duplicates(processed_pdfs)
            folder_scores = self._compute_folder_scores(processed_pdfs)
            findings = self._generate_findings(processed_pdfs)
            
            # Step 4: Save to storage
            self.logger.info("Step 4: Saving to storage...")
            self._save_to_storage(processed_pdfs)
            
            end_time = time.time()
            duration = end_time - start_time
            
            self.logger.info(f"Scan completed in {duration:.2f} seconds")
            
            return ScanResult(
                total_files=total_files,
                new_files=new_count,
                changed_files=changed_count,
                cached_files=cached_count,
                failed_files=failed_count,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                pdfs=processed_pdfs,
                stats=stats,
                duplicates=duplicates,
                folder_scores=folder_scores,
                findings=findings
            )
            
        except Exception as e:
            self.logger.error(f"Scan pipeline failed: {e}")
            raise
    
    def _discover_pdfs(self, root_path: str) -> List[str]:
        """
        Discover all PDF files in the given root path.
        
        Complexity: O(n) where n is number of files in the directory tree
        Memory: O(n) for storing file paths
        """
        path_obj = Path(root_path)
        if not path_obj.exists():
            raise ValueError(f"Path {root_path} does not exist")
        
        # Use Scanner to find all PDF files
        context = ScanContext(root_path=root_path, config={}, sqlite_conn=None, progress=None, logger=self.logger, start_time=time.time())
        return self.scanner.scan(context)
    
    def _process_files_parallel(self, pdf_paths: List[str]) -> tuple:
        """
        Process files in parallel using ThreadPoolExecutor.
        
        Complexity: O(n * processing_time) distributed across workers
        Memory: O(batch_size) for in-flight processing
        """
        processed_pdfs = []
        new_count = 0
        changed_count = 0
        cached_count = 0
        failed_count = 0
        
        # Process in batches to avoid memory issues
        total_batches = (len(pdf_paths) + self.batch_size - 1) // self.batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(pdf_paths))
            batch_paths = pdf_paths[start_idx:end_idx]
            
            self.logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch_paths)} files)")
            
            batch_results = self._process_batch_parallel(batch_paths)
            
            # Aggregate results
            for result in batch_results:
                if result:
                    processed_pdfs.append(result)
                    new_count += 1
                elif result is None:
                    # Check if it was cached or failed
                    # This is simplified; in practice we'd track status per file
                    pass
            
        # We'll track statuses more accurately by checking cache before processing
        # For now, we'll approximate
        total_processed = len(processed_pdfs)
        total_failed = len(pdf_paths) - total_processed
        
        # Estimate cached/changed counts
        cached_count = 0
        changed_count = 0
        if self.use_cache:
            for path in pdf_paths:
                if self.cache_manager and not self.cache_manager.is_changed(path):
                    cached_count += 1
            new_count = total_processed - cached_count
            changed_count = 0  # We don't track this precisely in this version
        else:
            new_count = total_processed
        
        return processed_pdfs, new_count, changed_count, cached_count, total_failed
    
    def _process_batch_parallel(self, pdf_paths: List[str]) -> List[Optional[PDFFile]]:
        """
        Process a batch of PDFs in parallel.
        
        Complexity: O(batch_size * processing_time / workers)
        Memory: O(batch_size) for storing results
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(self._process_single_file, path): path
                for path in pdf_paths
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    result = future.result(timeout=60)  # 60 second timeout per file
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Failed to process {path}: {e}")
                    results.append(None)
        
        return results
    
    def _process_single_file(self, pdf_path: str) -> Optional[PDFFile]:
        """
        Process a single PDF file through the pipeline.
        
        Complexity: O(1) for cache, O(file_size) for extraction and hashing
        Memory: O(1) for processing
        """
        try:
            # Check cache
            if self.use_cache and self.cache_manager:
                cached_pdf = self.cache_manager.load(pdf_path)
                if cached_pdf:
                    return cached_pdf
            
            # Extract metadata
            metadata = self.metadata_extractor.extract_metadata(pdf_path)
            if not metadata:
                return None
            
            # Extract first page text
            first_page_text = self.first_page_extractor.extract(pdf_path)
            
            # Create base PDFFile
            path_obj = Path(pdf_path)
            stats = path_obj.stat()
            
            pdf = PDFFile(
                path=pdf_path,
                filename=path_obj.name,
                parent_folder=str(path_obj.parent),
                size_bytes=stats.st_size,
                created_time=stats.st_ctime,
                modified_time=stats.st_mtime,
                hash=None,  # Will be computed later by duplicate detector
                page_count=metadata.get('page_count'),
                title=metadata.get('title'),
                author=metadata.get('author'),
                subject=metadata.get('subject'),
                keywords=metadata.get('keywords'),
                category="Unknown",
                subcategory=None,
                confidence=0.0,
                flags=[]
            )
            
            # Set flags
            if metadata.get('encrypted', False):
                pdf.flags.append("encrypted")
            
            # Classify
            category, confidence, _ = self.classifier.classify(pdf, first_page_text)
            pdf.category = category
            pdf.confidence = confidence
            
            # Cache the result
            if self.use_cache and self.cache_manager:
                self.cache_manager.save(pdf)
            
            return pdf
            
        except Exception as e:
            self.logger.error(f"Error processing {pdf_path}: {e}")
            return None
    
    def _analyze_statistics(self, pdfs: List[PDFFile]) -> Dict[str, Any]:
        """Compute statistics for the PDF collection."""
        if not pdfs:
            return {}
        return self.statistics_analyzer.compute(pdfs)
    
    def _find_duplicates(self, pdfs: List[PDFFile]) -> List[Any]:
        """Find duplicate PDFs."""
        if not pdfs:
            return []
        return self.duplicate_detector.find(pdfs)
    
    def _compute_folder_scores(self, pdfs: List[PDFFile]) -> Dict[str, Any]:
        """Compute folder quality scores."""
        if not pdfs:
            return {}
        return self.folder_scorer.compute(pdfs)
    
    def _generate_findings(self, pdfs: List[PDFFile]) -> List[Dict[str, Any]]:
        """Generate interesting findings."""
        if not pdfs:
            return []
        return self.interesting_finder.generate(pdfs)
    
    def _save_to_storage(self, pdfs: List[PDFFile]):
        """Save processed PDFs to SQLite storage."""
        if not pdfs:
            return
        
        try:
            self.sqlite_db.connect()
            for pdf in pdfs:
                self.sqlite_db.insert_pdf(pdf)
            self.sqlite_db.close()
            self.logger.info(f"Saved {len(pdfs)} PDFs to storage")
        except Exception as e:
            self.logger.error(f"Failed to save to storage: {e}")
    
    def _create_empty_result(self, start_time: float) -> ScanResult:
        """Create an empty result for when no PDFs are found."""
        end_time = time.time()
        return ScanResult(
            total_files=0,
            new_files=0,
            changed_files=0,
            cached_files=0,
            failed_files=0,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=end_time - start_time,
            pdfs=[],
            stats={},
            duplicates=[],
            folder_scores={},
            findings=[]
        )
    
    def get_scan_summary(self, result: ScanResult) -> str:
        """
        Generate a human-readable summary of the scan results.
        
        Complexity: O(1)
        """
        summary = f"""
PDF Scan Summary
================
Root Path: {result.root_path if hasattr(result, 'root_path') else 'Unknown'}
Duration: {result.duration_seconds:.2f} seconds
Total Files: {result.total_files}
New Files: {result.new_files}
Changed Files: {result.changed_files}
Cached Files: {result.cached_files}
Failed Files: {result.failed_files}

Statistics:
- Total PDFs: {result.stats.get('total_pdfs', 0)}
- Total Size: {result.stats.get('total_size_mb', 0)} MB
- Categories: {len(result.stats.get('category_breakdown', {}))}

Duplicates:
- Groups: {len(result.duplicates)}
- Total Duplicates: {sum(g.count for g in result.duplicates) if result.duplicates else 0}

Findings:
- Total Findings: {len(result.findings)}
- Top Finding: {result.findings[0]['title'] if result.findings else 'None'}
"""
        return summary