import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f)