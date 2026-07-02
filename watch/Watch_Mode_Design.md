# Watch Mode Design

## Overview
Watch Mode is an independent service that monitors configured directories for PDF file changes (create, delete, rename, modify) and triggers incremental updates to the SQLite cache. It runs as a daemon, reuses the existing SQLite cache and scanning pipeline, and minimises resource usage when idle. It is designed for long‑running execution with graceful recovery.

---

## 1. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Watch Service                            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Config Manager (directories, intervals, exclusions)     │ │
│  └───────────────────┬───────────────────────────────────────┘ │
│                      │                                         │
│  ┌───────────────────▼───────────────────────────────────────┐ │
│  │  File System Watcher (platform‑specific implementation)   │ │
│  │  - Detects events: created, deleted, modified, moved     │ │
│  └───────────────────┬───────────────────────────────────────┘ │
│                      │                                         │
│  ┌───────────────────▼───────────────────────────────────────┐ │
│  │  Event Queue (buffered, with deduplication)              │ │
│  └───────────────────┬───────────────────────────────────────┘ │
│                      │                                         │
│  ┌───────────────────▼───────────────────────────────────────┐ │
│  │  Incremental Update Pipeline                              │ │
│  │  - Debounce / coalesce events                            │ │
│  │  - Compare with cache (modified_time, size)              │ │
│  │  - Extract metadata only for changed files               │ │
│  │  - Update SQLite cache                                   │ │
│  └───────────────────┬───────────────────────────────────────┘ │
│                      │                                         │
│  ┌───────────────────▼───────────────────────────────────────┐ │
│  │  Error Recovery & Health Check                           │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
               Existing SQLite Cache
                         │
                         ▼
               PDF Inventory Services
```

The watch service is a standalone Python process that:
- Reads configuration (directories to watch, scan interval, exclusion patterns).
- Initialises a filesystem watcher.
- Processes events asynchronously.
- Calls the existing `CacheManager` and, if needed, the `Scanner` + `Extractor` + `Classifier` for changed files.

It does not modify the core architecture; it only uses the existing `CacheManager` and the same extraction/classification pipeline.

---

## 2. Package Layout

```
pdf_inventory/
├── watch/
│   ├── __init__.py
│   ├── service.py                # Main WatchService orchestrator
│   ├── watcher.py                # Filesystem watcher abstraction
│   ├── event_queue.py            # Event queue with deduplication
│   ├── updater.py                # Incremental update pipeline
│   ├── config.py                 # Watch-specific config (YAML/JSON)
│   ├── recovery.py               # Crash recovery (checkpoints)
│   ├── logging.py                # Rotating logs
│   └── platform/
│       ├── __init__.py
│       ├── linux.py              # inotify implementation
│       ├── windows.py            # ReadDirectoryChangesW
│       └── macos.py              # FSEvents
└── tests/
    └── watch/
        └── ...
```

---

## 3. Public Interfaces

### WatchService
```python
# service.py
```

### Watcher Abstraction
```python
# watcher.py
```

### IncrementalUpdater
```python
# updater.py
```

### Configuration
```python
# config.py
```

---

## 4. Event Queue & Deduplication

- The queue is a thread‑safe priority queue (or asyncio queue) that stores events.
- Events are deduplicated: if multiple events for the same file occur within a short time window (debounce), only the latest is processed.
- The queue can be backed by a small in‑memory buffer; if the service crashes, we lose only events not yet processed (but we can recover by doing a full directory scan on restart, or using a persistent queue like SQLite).

### Debouncing
We implement a debouncer that aggregates events for the same file path and emits a single `MODIFIED` event after a quiet period (e.g., 2 seconds). This prevents re‑processing the same file multiple times during a save operation.

---

## 5. Incremental Update Pipeline

When the updater receives a batch of events:
1. **Filter** events against exclusion patterns.
2. **Group** by file path and event type. For `MOVED`, we need to update the path in the cache.
3. For each unique file:
   - If event is `DELETED`: remove entry from cache.
   - If `MODIFIED` or `CREATED`: check if the file exists and is a PDF.
   - Compare current `modified_time` and `size` with cache entry (if exists).
   - If changed, extract metadata (using `MetadataExtractor` and `FirstPageExtractor`), classify, and update the cache via `CacheManager.save()`.
   - If unchanged, do nothing.
4. **Atomic updates**: Use SQLite transactions to ensure consistency.
5. **Logging**: Log each updated file.

### Handling Renames (MOVED)
On a move event, we get source and destination paths. We should update the `path` field in the cache for that PDFFile to the new path, preserving all other metadata. If the source path is not in cache, treat as a creation.

### Periodic Full Sync
Even with event watching, we should periodically (e.g., daily) perform a full directory scan to catch any missed changes (e.g., events dropped due to queue overflow, or files modified while watcher was down). This can be done by comparing the entire directory tree with the cache and updating any discrepancies. The scan can be performed in the background with low priority.

---

## 6. Configuration

Configuration can be stored in a YAML or JSON file, with command‑line overrides. Example:

```yaml
# watch_config.yaml
```

---

## 7. Logging

- Use rotating file logs (e.g., `RotatingFileHandler`).
- Log level: INFO for normal events, DEBUG for detailed file operations.
- Log format: timestamp, level, message.
- Include file paths in logs for audit.

---

## 8. Error Recovery

- **Crash recovery**: On startup, the service should check if a previous instance crashed. It can:
  - Read a checkpoint file (last processed event timestamp) to resume from.
  - Perform a full directory scan to synchronise state, because events may have been lost.
- **Queue persistence**: Use an SQLite queue to store events that are not yet processed, so they survive restarts.
- **Idempotent updates**: The update pipeline is idempotent; reprocessing the same event multiple times does not corrupt the cache.
- **Health checks**: The service can expose a health endpoint (e.g., a unix socket) to check if it's running and its last successful sync time.

---

## 9. Platform‑Specific Implementations

| Platform | Recommended Library | Pros | Cons |
|----------|---------------------|------|------|
| **Linux** | `inotify` via `watchdog` (which uses `inotify`) | Mature, efficient, kernel‑supported. | Linux‑only. |
| **Windows** | `watchdog` (uses `ReadDirectoryChangesW`) | Native Windows API. | Slightly higher overhead. |
| **macOS** | `watchdog` (uses `FSEvents` via `pyobjc-framework-CoreServices`) | Efficient, supports file events. | Requires pyobjc. |

**Recommendation**: Use the `watchdog` library. It provides a unified API and automatically selects the best backend for each platform. We can still implement custom watchers if more control is needed, but `watchdog` is reliable and widely used. Additionally, we can fall back to periodic polling if the native watcher fails (e.g., on network drives).

### Polling Fallback
For environments where filesystem events are unreliable (e.g., network drives), we can implement a polling watcher that scans directories every `scan_interval` seconds and compares the state with the cache. This is less efficient but works everywhere.

---

## 10. Performance Considerations

- **Event storm handling**: When a large number of files are added/modified (e.g., after a download), the event queue can flood. We use debouncing and coalescing to reduce processing.
- **I/O throttling**: Limit the number of concurrent file operations (metadata extraction) using a semaphore to avoid disk thrashing.
- **Memory usage**: The event queue size is bounded; old events are dropped if the queue is full (with a warning log).
- **CPU**: When idle, the watcher uses negligible CPU (the native API is interrupt‑driven). The periodic full scan runs at a low priority.

---

## 11. Integration with Existing Services

- The watch service reuses:
  - `CacheManager` for checking if files are changed and for saving updates.
  - `MetadataExtractor` and `FirstPageExtractor` for PDF parsing.
  - `RuleClassifier` for classification.
- It does not use the full `Scanner` pipeline because it processes individual files.
- It does not trigger the full analysis (statistics, duplicates, etc.) on each change; instead, it only updates the cache. The main analysis can be run periodically (e.g., weekly) by the main CLI, which will read from the updated cache.

---

## 12. Example Sequence

1. User saves a new PDF `invoice.pdf` in `~/Documents`.
2. The watch service receives a `CREATED` event.
3. The event is debounced and then passed to the updater.
4. The updater checks the cache: path not found.
5. It calls `MetadataExtractor` to get metadata and page count.
6. It calls `FirstPageExtractor` to get first page text.
7. It calls `RuleClassifier` to assign a category.
8. It saves the new `PDFFile` entry via `CacheManager.save()`.
9. The cache is updated.
10. The main CLI, when run later, will show the new file without rescanning everything.

---

## 13. Future Enhancements

- **Push notifications**: Notify the main application (via IPC or websocket) when changes occur, so that the UI can update live.
- **Multi‑folder support with separate caches**: Allow per‑directory cache or a single global cache.
- **Conflict resolution**: If a file is modified while the service is down, the full sync will detect the change.
- **Suspend/resume**: Pause watching during high system load.
