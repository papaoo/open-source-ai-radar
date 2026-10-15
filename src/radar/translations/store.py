"""Disk cache for translated strings (source text -> translation).

A flat JSON map keeps the pipeline incremental: each run loads the cache, only
sends unseen sources to the provider, and writes the merged result back. Many
projects share identical descriptions, so keying by source text (not repo)
maximizes reuse and keeps the file small.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_cache(path: Path) -> dict[str, str]:
    """Read the cache map, tolerating a missing or corrupt file."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("translation cache at %s unreadable (%s), starting fresh", path, exc)
        return {}


def save_cache(path: Path, mapping: dict[str, str]) -> None:
    """Atomically write the cache map as UTF-8 JSON (sorted for stable diffs)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(mapping, ensure_ascii=False, sort_keys=True, indent=0)
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)
