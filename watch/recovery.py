import json
import time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class RecoveryManager:
    def __init__(self, state_dir: str):
        self.state_dir = Path(state_dir).expanduser()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.state_dir / "checkpoint.json"
        self.last_processed = 0.0

    def load(self):
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file) as f:
                    data = json.load(f)
                    self.last_processed = data.get("last_processed", 0.0)
                logger.info(f"Recovered state: last_processed={self.last_processed}")
            except Exception as e:
                logger.error(f"Failed to load checkpoint: {e}")

    def checkpoint(self):
        try:
            with open(self.checkpoint_file, "w") as f:
                json.dump({"last_processed": time.time()}, f)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def save(self):
        self.checkpoint()