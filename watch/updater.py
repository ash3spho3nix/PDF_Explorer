import logging
from typing import List
from pathlib import Path
from .event_queue import FileEvent, EventType
from storage.cache import CacheManager
from extractor.metadata import MetadataExtractor
from extractor.first_page import FirstPageExtractor
from classifier.rules import RuleClassifier
from models.pdf_file import PDFFile

logger = logging.getLogger(__name__)


class IncrementalUpdater:
    def __init__(self, cache_manager: CacheManager,
                 metadata_extractor: MetadataExtractor,
                 first_page_extractor: FirstPageExtractor,
                 classifier: RuleClassifier):
        self.cache = cache_manager
        self.metadata_extractor = metadata_extractor
        self.first_page_extractor = first_page_extractor
        self.classifier = classifier

    def process_events(self, events: List[FileEvent]):
        for event in events:
            try:
                self._process_single(event)
            except Exception as e:
                logger.error(f"Failed to process event {event}: {e}")

    def _process_single(self, event: FileEvent):
        if event.type == EventType.DELETED:
            # Remove from cache (if exists)
            # We'll mark it as deleted by updating the cache entry with a flag
            # or we can delete the row. We'll delete.
            self.cache.delete(event.path)
            return

        if event.type == EventType.MOVED and event.dest_path:
            # Update path in cache
            self.cache.update_path(event.path, event.dest_path)
            # Then process as modified at new path
            event.path = event.dest_path

        # For CREATED and MODIFIED, re-extract
        if not Path(event.path).exists():
            return
        # Check if file is PDF
        if not event.path.lower().endswith(".pdf"):
            return

        # Compare with cache
        if not self.cache.is_changed(event.path):
            return

        # Extract metadata
        metadata = self.metadata_extractor.extract_metadata(event.path)
        if not metadata:
            return
        first_page = self.first_page_extractor.extract(event.path)

        # Build PDFFile
        p = Path(event.path)
        stat = p.stat()
        pdf = PDFFile(
            path=event.path,
            filename=p.name,
            parent_folder=str(p.parent),
            size_bytes=stat.st_size,
            created_time=stat.st_ctime,
            modified_time=stat.st_mtime,
            hash=None,
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
        if metadata.get('encrypted', False):
            pdf.flags.append("encrypted")
        # Classify
        classification = self.classifier.classify(pdf, first_page)
        pdf.category = classification.category
        pdf.subcategory = classification.subcategory
        pdf.confidence = classification.confidence
        pdf.classification_explanation = classification.reasoning

        # Save to cache
        self.cache.save(pdf)
        logger.info(f"Updated {event.path}")