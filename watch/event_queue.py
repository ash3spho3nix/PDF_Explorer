import queue
import time
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum
import threading


class EventType(Enum):
    CREATED = "created"
    DELETED = "deleted"
    MODIFIED = "modified"
    MOVED = "moved"


@dataclass
class FileEvent:
    type: EventType
    path: str
    dest_path: Optional[str] = None


class EventQueue:
    def __init__(self, debounce_delay: float = 2.0):
        self._queue = queue.Queue()
        self._debounce_delay = debounce_delay
        self._pending: dict[str, FileEvent] = {}
        self._lock = threading.Lock()
        self._last_emit = time.time()

    def put(self, event: FileEvent):
        with self._lock:
            self._pending[event.path] = event

    def get_batch(self, timeout: float = 0.5) -> List[FileEvent]:
        # Flush pending events after debounce delay or timeout
        now = time.time()
        if now - self._last_emit >= self._debounce_delay:
            with self._lock:
                if self._pending:
                    events = list(self._pending.values())
                    self._pending.clear()
                    self._last_emit = now
                    return events
        # If nothing, wait for a new event
        try:
            ev = self._queue.get(timeout=timeout)
            self.put(ev)
        except queue.Empty:
            pass
        # Try again after short sleep (recursive not recommended)
        # Instead, we'll process pending if any
        with self._lock:
            if self._pending and (now - self._last_emit) >= self._debounce_delay:
                events = list(self._pending.values())
                self._pending.clear()
                self._last_emit = now
                return events
        return []