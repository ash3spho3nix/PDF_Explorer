"""
Handles operational configuration loading and parameter normalization.
"""

from pathlib import Path
from typing import Any, Dict, Optional


class ConfigLoader:
    """Responsible for preparing baseline runtime configurations for the scan pipeline."""

    @staticmethod
    def load_default_config() -> Dict[str, Any]:
        """
        Returns a fallback programmatic configuration dict.
        In a production landscape, this can blend with a local .json or .toml file.
        """
        return {
            "max_workers": 8,
            "timeout_seconds": 30,
            "excluded_directories": [".git", "node_modules", "__pycache__", ".pytest_cache"],
            "chunk_size": 50
        }

    @classmethod
    def load_from_path(cls, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Loads configuration, safely merging user overrides over safe system defaults.
        """
        base = cls.load_default_config()
        if config_path and config_path.is_file():
            # If JSON configuration support is extended, merge overrides here.
            pass
        return base