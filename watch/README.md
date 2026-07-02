# Watch Mode

Automatically monitors configured directories for PDF changes and updates the inventory cache incrementally.

## Features
- Detects created, modified, deleted, and moved PDFs
- Reuses existing SQLite cache
- Debounces events to avoid repeated processing
- Supports crash recovery with checkpoints
- Platform‑specific backends (inotify, FSEvents, ReadDirectoryChangesW)

## Installation
```bash
pip install -e .