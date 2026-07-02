# scanner/pipeline.py
from typing import List, Optional, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime
import time
import logging
from dataclasses import dataclass, field

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
    root_path: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessOutcome:
    pdf: Optional[PDFFile]
    status: str
    message: Optional[str] = None


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
        logger: Optional[logging.Logger] = None,
        progress: Optional[Any] = None
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
        self.progress = progress
        self.processing_task_id: Optional[int] = None
        
        # Initialize components
        self.cache_manager = CacheManager(cache_path, logger=self.logger) if use_cache else None
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
            scan_start = time.time()
            pdf_paths = self._discover_pdfs(root_path)
            scan_end = time.time()
            total_files = len(pdf_paths)
            self.logger.info(f"Found {total_files} PDF files")
            
            if not pdf_paths:
                self.logger.warning("No PDF files found")
                return self._create_empty_result(start_time)
            
            if self.progress is not None:
                self.processing_task_id = self.progress.add_task(
                    "Processing PDFs",
                    total=total_files,
                    cached=0,
                    new=0,
                    changed=0,
                    failed=0,
                    current_file=""
                )
            
            # Step 2: Process files in parallel
            self.logger.info(f"Step 2: Processing files with {self.max_workers} workers...")
            process_start = time.time()
            processed_pdfs, new_count, changed_count, cached_count, failed_count = self._process_files_parallel(pdf_paths)
            
            # Step 3: Analyze results
            self.logger.info("Step 3: Analyzing results...")
            process_end = time.time()
            analysis_start = time.time()
            stats = self._analyze_statistics(processed_pdfs)
            duplicates = self._find_duplicates(processed_pdfs)
            folder_scores = self._compute_folder_scores(processed_pdfs)
            findings = self._generate_findings(processed_pdfs)
            analysis_end = time.time()
            
            # Step 4: Save to storage
            self.logger.info("Step 4: Saving to storage...")
            storage_start = time.time()
            self._save_to_storage(processed_pdfs)
            storage_end = time.time()
            
            end_time = time.time()
            duration = end_time - start_time
            
            metrics = {
                "scan_duration": scan_end - scan_start,
                "processing_duration": process_end - process_start,
                "analysis_duration": analysis_end - analysis_start,
                "storage_duration": storage_end - storage_start,
                "total_duration": duration,
                "pdfs_processed": total_files,
                "new_files": new_count,
                "changed_files": changed_count,
                "cached_files": cached_count,
                "failed_files": failed_count,
                "pdfs_per_second": total_files / duration if duration > 0 else 0.0,
            }
            
            self.logger.info(f"Scan completed in {duration:.2f} seconds")
            
            # Build a ScanReport-like object for downstream report generation compatibility
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
                findings=findings,
                root_path=root_path,
                metrics=metrics
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
            
            batch_outcomes = self._process_batch_parallel(batch_paths)

            for path, outcome in batch_outcomes:
                if outcome.pdf:
                    processed_pdfs.append(outcome.pdf)
                if outcome.status == "new":
                    new_count += 1
                elif outcome.status == "changed":
                    changed_count += 1
                elif outcome.status == "cached":
                    cached_count += 1
                elif outcome.status == "failed":
                    failed_count += 1

                # Update progress UI with latest counters and current file
                try:
                    if self.progress is not None and self.processing_task_id is not None:
                        self.progress.update(
                            self.processing_task_id,
                            advance=1,
                            cached=cached_count,
                            new=new_count,
                            changed=changed_count,
                            failed=failed_count,
                            current_file=(Path(path).name if path else "")
                        )
                except Exception:
                    # Progress update is best-effort; do not fail the pipeline on UI errors
                    pass
        
        return processed_pdfs, new_count, changed_count, cached_count, failed_count

    def _process_batch_parallel(self, pdf_paths: List[str]) -> List[Tuple[str, ProcessOutcome]]:
        """
        Process a batch of PDFs in parallel.
        """
        outcomes: List[Tuple[str, ProcessOutcome]] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(self._process_single_file, path): path
                for path in pdf_paths
            }
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    outcome = future.result(timeout=60)
                    outcomes.append((path, outcome))
                except Exception as e:
                    self.logger.error(f"Failed to process {path}: {e}")
                    outcomes.append((path, ProcessOutcome(pdf=None, status="failed", message=str(e))))
                finally:
                    if self.progress is not None and self.processing_task_id is not None:
                        self.progress.update(
                            self.processing_task_id,
                            advance=1,
                            current_file=path
                        )
        return outcomes

    def _process_single_file(self, pdf_path: str) -> ProcessOutcome:
        """
        Process a single PDF file through the pipeline.
        
        Complexity: O(1) for cache, O(file_size) for extraction and hashing
        Memory: O(1) for processing
        """
        status = "new"
        try:
            if self.use_cache and self.cache_manager:
                status = self.cache_manager.get_entry_status(pdf_path)
                if status == "cached":
                    cached_pdf = self.cache_manager.load(pdf_path)
                    if cached_pdf:
                        self.logger.debug(f"Cache hit: {pdf_path}")
                        return ProcessOutcome(pdf=cached_pdf, status="cached")
                    status = "changed"
                elif status == "changed":
                    self.logger.debug(f"Cache stale: {pdf_path}")
                else:
                    self.logger.debug(f"Cache miss: {pdf_path}")
            
            metadata = self.metadata_extractor.extract_metadata(pdf_path)
            if not metadata:
                return ProcessOutcome(pdf=None, status="failed", message="metadata extraction failed")
            
            first_page_text = self.first_page_extractor.extract(pdf_path)
            
            path_obj = Path(pdf_path)
            stats = path_obj.stat()
            
            pdf = PDFFile(
                path=pdf_path,
                filename=path_obj.name,
                parent_folder=str(path_obj.parent),
                size_bytes=stats.st_size,
                created_time=stats.st_ctime,
                modified_time=stats.st_mtime,
                hash=None,
                page_count=metadata.get('page_count'),
                title=metadata.get('title'),
                author=metadata.get('author'),
                subject=metadata.get('subject'),
                keywords=metadata.get('keywords'),
                category="Unknown",
                subcategory=None,
                confidence=0.0,
                flags=[],
                classification_explanation=None
            )
            
            if metadata.get('encrypted', False):
                pdf.flags.append("encrypted")
            
            classification = self.classifier.classify(pdf, first_page_text)
            pdf.category = classification.category
            pdf.subcategory = classification.subcategory
            pdf.confidence = classification.confidence
            pdf.classification_explanation = classification.reasoning
            
            if self.use_cache and self.cache_manager:
                self.cache_manager.save(pdf)
            
            return ProcessOutcome(pdf=pdf, status=status)
            
        except Exception as e:
            self.logger.error(f"Error processing {pdf_path}: {e}")
            return ProcessOutcome(pdf=None, status="failed", message=str(e))
    
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
            findings=[],
            metrics={
                "scan_duration": 0.0,
                "processing_duration": 0.0,
                "analysis_duration": 0.0,
                "storage_duration": 0.0,
                "total_duration": end_time - start_time,
                "pdfs_processed": 0,
                "new_files": 0,
                "changed_files": 0,
                "cached_files": 0,
                "failed_files": 0,
                "pdfs_per_second": 0.0,
            }
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