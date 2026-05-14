import os
import json
from pathlib import Path


class Config:
    def __init__(self, config_dir=None):
        self._dir = Path(config_dir or os.path.join(os.path.expanduser("~"), ".deepseek-widget"))
        self._dir.mkdir(parents=True, exist_ok=True)
        self._file = self._dir / "config.json"
        self._data = {}
        self._load()

    def _load(self):
        if self._file.exists():
            try:
                self._data = json.loads(self._file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self):
        self._file.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def get_api_key(self):
        return self._data.get("api_key")

    def set_api_key(self, key):
        self._data["api_key"] = key
        self._save()

    def get_refresh_interval(self):
        return self._data.get("refresh_interval", 300)

    def set_refresh_interval(self, seconds):
        self._data["refresh_interval"] = seconds
        self._save()
