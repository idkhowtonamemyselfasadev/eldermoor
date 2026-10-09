"""The string table: data/text/<lang>.json, looked up by dotted key."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eldermoor.config import DATA


class Text:
    """Flat key -> string (or list of strings) table with %-style formatting."""

    def __init__(self, entries: dict[str, Any], language: str = "en") -> None:
        self.entries = entries
        self.language = language

    @classmethod
    def load(cls, language: str = "en", root: Path = DATA) -> Text:
        """Read data/text/<language>.json, falling back to English."""
        path = root / "text" / f"{language}.json"
        if not path.exists():
            path = root / "text" / "en.json"
            language = "en"
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls({k: v for k, v in raw.items() if not k.startswith("_")}, language)

    def has(self, key: str) -> bool:
        """True if the key exists."""
        return key in self.entries

    def get(self, key: str, **fmt: Any) -> str:
        """One string. A missing key returns the key itself so nothing ever blanks out."""
        value = self.entries.get(key)
        if value is None:
            return key
        if isinstance(value, list):
            value = " ".join(value)
        return value.format(**fmt) if fmt else value

    def pages(self, key: str, **fmt: Any) -> list[str]:
        """A dialogue entry as a list of pages (a plain string is one page)."""
        value = self.entries.get(key)
        if value is None:
            return [key]
        pages = value if isinstance(value, list) else [value]
        return [p.format(**fmt) if fmt else p for p in pages]

    def keys_with_prefix(self, prefix: str) -> list[str]:
        """All keys starting with the prefix, sorted (used by validation)."""
        return sorted(k for k in self.entries if k.startswith(prefix))
