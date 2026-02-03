import json
import os
import threading
from datetime import datetime
from typing import Any


class JsonStore:
    """Thread-safe JSON file store for simple persistence."""

    def __init__(self, file_path: str):
        self._file_path = file_path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({"meta": {"createdAt": datetime.utcnow().isoformat()}, "items": []}, f)

    def read_all(self) -> dict[str, Any]:
        with self._lock:
            with open(self._file_path, "r", encoding="utf-8") as f:
                return json.load(f)

    def write_all(self, data: dict[str, Any]) -> None:
        with self._lock:
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
