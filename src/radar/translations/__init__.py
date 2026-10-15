"""Build-time machine translation for AI Radar UI data (project descriptions).

Public API:
    - :func:`collect_descriptions` — unique English descriptions from an export.
    - :func:`translate_descriptions` — incremental, cached translation driver.

The subsystem is intentionally optional: with no cache file, no network or no
provider, it does nothing harmful — pages keep their English descriptions. Only
``radar translate`` (or the guarded CI job) populates the cache.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from radar.translations.providers import Translator, get_provider
from radar.translations.store import load_cache, save_cache

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_INDEX_PATH",
    "DEFAULT_OUT_PATH",
    "REPO_ROOT",
    "collect_descriptions",
    "get_provider",
    "load_cache",
    "save_cache",
    "translate_descriptions",
]

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INDEX_PATH = REPO_ROOT / "data" / "exports" / "projects-index.json"
DEFAULT_OUT_PATH = REPO_ROOT / "data" / "exports" / "descriptions.zh.json"


def collect_descriptions(index_path: Path) -> list[str]:
    """Return unique project descriptions, most-visible first.

    Ordered by radar score (descending) so the first translated chunks cover
    the projects readers actually land on (home, top, trending, category).
    Identical descriptions across repos are de-duplicated, keeping the
    highest-ranked occurrence.
    """
    if not index_path.exists():
        logger.warning("index export not found at %s", index_path)
        return []
    try:
        with open(index_path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("failed to read %s: %s", index_path, exc)
        return []

    def _score(p: dict[str, Any]) -> float:
        try:
            return float(p.get("radar_score") or 0)
        except (TypeError, ValueError):
            return 0.0

    out: list[str] = []
    seen: set[str] = set()
    for p in sorted(data.get("projects", []) or [], key=_score, reverse=True):
        desc = (p.get("description") or "").strip()
        if desc and desc not in seen:
            seen.add(desc)
            out.append(desc)
    return out


def translate_descriptions(
    *,
    index_path: Path = DEFAULT_INDEX_PATH,
    out_path: Path = DEFAULT_OUT_PATH,
    provider: Translator | None = None,
    target: str = "zh-CN",
    limit: int | None = None,
    force: bool = False,
    dry_run: bool = False,
    chunk_size: int = 100,
) -> dict[str, Any]:
    """Translate unseen descriptions into a cached JSON map.

    Returns a stats dict. Idempotent and incremental: already-cached sources are
    skipped unless ``force``. When ``dry_run`` is set, no network call happens
    and nothing is written.
    """
    cache = load_cache(out_path)
    sources = collect_descriptions(index_path)

    pending = list(sources) if force else [s for s in sources if s not in cache]

    if limit is not None:
        pending = pending[:limit]

    stats: dict[str, Any] = {
        "provider": (provider or get_provider("auto")).name,
        "total_sources": len(sources),
        "cached": len(cache),
        "pending": len(pending),
        "translated": 0,
        "cache_size": len(cache),
        "dry_run": dry_run,
    }

    if dry_run or not pending:
        return stats

    translator = provider or get_provider("auto")
    # Translate and persist in chunks so a long first run is resumable: each
    # batch is flushed to the cache immediately, so an interruption never
    # loses completed work and the next run only fills the remaining gaps.
    total_done = 0
    for i in range(0, len(pending), max(1, chunk_size)):
        batch = pending[i : i + chunk_size]
        translated = translator.translate(batch, target)
        if translated:
            cache.update(translated)
            save_cache(out_path, cache)
        total_done += len(translated)
        logger.info(
            "translated %d/%d pending (%s), cache now %d",
            total_done,
            len(pending),
            translator.name,
            len(cache),
        )

    stats["translated"] = total_done
    stats["cache_size"] = len(cache)
    return stats
