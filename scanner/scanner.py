"""
Coordinates filesystem candidate extraction and target tracking execution passes.
"""

from pathlib import Path
from typing import List
from models.scan_context import ScanContext
from scanner.discovery import DirectoryDiscovery


class Scanner:
    """Manages full directory inspection processes conforming to Core Pipeline design specifications."""

    def scan(self, context: ScanContext) -> List[str]:
        """
        Inspects targeted infrastructure boundaries. Returns absolute path string locations.
        """
        root_dir = Path(context.root_path)
        excluded = set(context.config.get("excluded_directories", []))
        
        discoverer = DirectoryDiscovery(exclude_names=excluded)
        found_paths: List[str] = []

        if context.logger:
            context.logger.info(f"[bold blue]Scanning filesystem targets at:[/bold blue] {root_dir}")

        for verified_path in discoverer.discover_candidates(root_dir):
            absolute_string = str(verified_path.resolve())
            found_paths.append(absolute_string)
            
            # Record base counters inside global scan matrix
            context.stats["total_pdfs"] += 1
            try:
                context.stats["total_size_bytes"] += verified_path.stat().st_size
            except OSError:
                pass

        return found_paths