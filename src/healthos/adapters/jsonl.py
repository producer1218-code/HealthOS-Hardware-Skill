"""Read canonical JSONL produced by another adapter or the synthetic demo."""
from pathlib import Path

from healthos.io import read_jsonl


class JsonlAdapter:
    def read(self, path: Path, user_id: str):
        for item in read_jsonl(path):
            if item.user_id != user_id:
                raise ValueError("JSONL user_id differs from configured user_id")
            yield item
