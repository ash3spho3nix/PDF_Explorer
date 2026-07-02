import logging
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from .event_queue import FileEvent, EventType

logger = logging.getLogger(__name__)


class PDFEventHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[FileEvent], None], exclude_patterns: list):
        self.callback = callback
        self.exclude_patterns = exclude_patterns

    def _should_ignore(self, path: str) -> bool:
        p = Path(path)
        for pattern in self.exclude_patterns:
            if p.match(pattern):
                return True
        return False

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".pdf"):
            if not self._should_ignore(event.src_path):
                self.callback(FileEvent(EventType.CREATED, event.src_path))

    def on_modified(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".pdf"):
            if not self._should_ignore(event.src_path):
                self.callback(FileEvent(EventType.MODIFIED, event.src_path))

    def on_deleted(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".pdf"):
            if not self._should_ignore(event.src_path):
                self.callback(FileEvent(EventType.DELETED, event.src_path))

    def on_moved(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".pdf"):
            if not self._should_ignore(event.src_path) and not self._should_ignore(event.dest_path):
                self.callback(FileEvent(EventType.MOVED, event.src_path, event.dest_path))


class FileWatcher:
    def __init__(self, directories: list, exclude_patterns: list,
                 callback: Callable[[FileEvent], None]):
        self.directories = directories
        self.exclude_patterns = exclude_patterns
        self.callback = callback
        self.observer = Observer()
        self.handler = PDFEventHandler(callback, exclude_patterns)

    def start(self):
        for dir_path in self.directories:
            path = Path(dir_path)
            if path.exists():
                self.observer.schedule(self.handler, str(path), recursive=True)
            else:
                logger.warning(f"Directory {dir_path} does not exist, skipping")
        self.observer.start()
        logger.info(f"Watching {len(self.directories)} directories")

    def stop(self):
        self.observer.stop()
        self.observer.join()
        logger.info("Watch stopped")