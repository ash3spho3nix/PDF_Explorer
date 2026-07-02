import time
import signal
import logging
from typing import Optional
from .config import WatchConfig
from .watcher import FileWatcher
from .event_queue import EventQueue
from .updater import IncrementalUpdater
from .recovery import RecoveryManager
from storage.cache import CacheManager
from extractor.metadata import MetadataExtractor
from extractor.first_page import FirstPageExtractor
from classifier.rules import RuleClassifier

logger = logging.getLogger(__name__)


class WatchService:
    def __init__(self, config: WatchConfig):
        self.config = config
        self.running = False
        self.queue = EventQueue(debounce_delay=config.debounce_delay)
        self.cache_manager = CacheManager(config.cache_path)
        self.metadata_extractor = MetadataExtractor()
        self.first_page_extractor = FirstPageExtractor()
        self.classifier = RuleClassifier()
        self.updater = IncrementalUpdater(
            self.cache_manager,
            self.metadata_extractor,
            self.first_page_extractor,
            self.classifier
        )
        self.recovery = RecoveryManager(config.state_dir)
        self.watcher = FileWatcher(
            config.directories,
            config.exclude_patterns,
            self.queue.put
        )

    def start(self):
        # Load recovery state
        self.recovery.load()
        self.running = True
        self.watcher.start()

        # Set up signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("Watch service started")
        while self.running:
            events = self.queue.get_batch(timeout=1.0)
            if events:
                self.updater.process_events(events)
                self.recovery.checkpoint()

    def stop(self):
        self.running = False
        self.watcher.stop()
        self.recovery.save()
        logger.info("Watch service stopped")

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, stopping...")
        self.stop()