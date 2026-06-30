"""
Filesystem discovery processing pipelines designed to identify candidates for indexing.
"""

from pathlib import Path
from typing import List, Set, Generator, Optional


class DirectoryDiscovery:
    """Exposes processing mechanisms to walk directories looking for PDF targets."""

    def __init__(self, exclude_names: Optional[Set[str]] = None):
        self.exclude_names = exclude_names or set()

    def _should_skip(self, path: Path) -> bool:
        """Determines if a structural segment or item crosses exclusions."""
        return any(part in self.exclude_names for part in path.parts)

    def discover_candidates(self, root_path: Path) -> Generator[Path, None, None]:
        """
        Generates clean paths pointing towards files matching candidate selectors.
        Defends runtime from hitting unreadable symlinks or cyclic paths.
        """
        if not root_path.exists():
            return

        try:
            for item in root_path.rglob("*.pdf"):
                try:
                    if item.is_file() and not self._should_skip(item):
                        yield item
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            return