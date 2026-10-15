"""Chinese "opportunity brief" generator — an optional P3 cost-gated layer.

For the top-N surfaced opportunities, ask the Groq model for a 2-4 sentence
Chinese note explaining *why it is worth watching, who is behind it, and the
main risk*. Kept strictly incremental and cheap, mirroring the translation
subsystem's money-control pattern:

- cache key is ``repo_full_name`` and each entry stores a *signal fingerprint*;
  a repo is only re-briefed when its tier or leading signals materially change;
- every brief is flushed to disk immediately, so an interrupted run never loses
  completed work and the next run only fills the remaining gaps;
- with no ``GROQ_API_KEYS``, a 429, or any failure, generation is skipped —
  callers fall back to a template sentence and try again next run.

Nothing here is required for the site to build: absent briefs simply do not
appear and the frontend shows the template blurb instead.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT_PATH = REPO_ROOT / "data" / "exports" / "opportunity-briefs.json"
DEFAULT_DIGEST_STATE_PATH = REPO_ROOT / "data" / ".opportunity_digest_state.json"

#: How many top candidates get an AI brief per run (cheapest-first ordering).
DEFAULT_BRIEF_LIMIT = 30

TIER_LABELS_ZH: dict[str, str] = {
    "blue_ocean": "蓝海机会",
    "high_potential": "高潜力",
    "watch": "观察",
}

#: Ordered tier ranks — used to detect upgrades for the daily digest.
TIER_RANK: dict[str, int] = {"watch": 1, "high_potential": 2, "blue_ocean": 3}


def load_briefs(path: Path = DEFAULT_OUT_PATH) -> dict[str, Any]:
    """Read the brief cache map, tolerating a missing or corrupt file."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("brief cache at %s unreadable (%s), starting fresh", path, exc)
        return {}


def save_briefs(path: Path, mapping: dict[str, Any]) -> None:
    """Atomically write the brief cache as UTF-8 JSON (sorted for stable diffs)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(mapping, ensure_ascii=False, sort_keys=True, indent=2)
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def signal_fingerprint(candidate: dict[str, Any]) -> str:
    """Stable hash of the signals that should trigger a re-brief.

    Only coarse buckets are used so tiny day-to-day jitter does not burn API
    budget — a repo is re-briefed when its tier changes or a leading indicator
    crosses a bucket boundary.
    """
    tier = str(candidate.get("tier", ""))
    accel = round(float(candidate.get("star_growth_acceleration", 1.0) or 1.0), 1)
    contrib = int(candidate.get("contributors_7d", 0) or 0) // 5
    vel_bucket = int(float(candidate.get("velocity", 0) or 0)) // 10
    stars_bucket = int(float(candidate.get("stars", 0) or 0)) // 500
    raw = f"{tier}|{accel}|{contrib}|{vel_bucket}|{stars_bucket}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _fmt(n: Any) -> str:
    try:
        value = float(n)
    except (TypeError, ValueError):
        return "0"
    if value >= 1000:
        return f"{value / 1000:.1f}k"
    return str(int(value))


def template_brief(candidate: dict[str, Any]) -> str:
    """Deterministic Chinese fallback when no AI brief is available yet."""
    name = candidate.get("repo_full_name", "")
    cat = candidate.get("category") or "该赛道"
    tier_zh = TIER_LABELS_ZH.get(candidate.get("tier", ""), "早期机会")
    lang = candidate.get("language") or ""
    who = f"以 {lang} 为主" if lang else "多语言协作"
    accel = candidate.get("star_growth_acceleration", 1.0) or 1.0
    contrib = int(candidate.get("contributors_7d", 0) or 0)
    health = int(float(candidate.get("health", 0) or 0))
    risk = "维护者较集中、需持续关注稳定性" if health < 65 else "健康度尚可、风险相对可控"
    return (
        f"{name} 被判定为{tier_zh}：处于 {cat} 赛道、{who}，"
        f"近 7 天 star 加速度约 {accel:.1f}x、新增贡献者 {contrib} 人，"
        f"领先指标强劲但尚未被主流定价。主要风险：{risk}。"
    )


def _build_prompt(candidate: dict[str, Any]) -> str:
    comp = candidate.get("components", {}) or {}
    lines = [
        f"仓库：{candidate.get('repo_full_name', '')}",
        f"分类：{candidate.get('category') or '未知'}"
        + (f" / {candidate.get('sub_category')}" if candidate.get("sub_category") else ""),
        f"主要语言：{candidate.get('language') or '未知'}",
        f"Stars：{candidate.get('stars', 0)}（近7天 +{candidate.get('stars_7d', 0)}）",
        f"机会分档：{TIER_LABELS_ZH.get(candidate.get('tier', ''), candidate.get('tier', ''))}",
        f"机会总分：{candidate.get('opportunity_score', 0)}",
        f"领先信号：速度(velocity)={candidate.get('velocity', 0)}, "
        f"加速度={candidate.get('star_growth_acceleration', 1.0)}x, "
        f"7天新增贡献者={candidate.get('contributors_7d', 0)}, "
        f"7天新增fork={candidate.get('forks_7d', 0)}",
        f"可持续性：健康度={candidate.get('health', 0)}, "
        f"早期性={comp.get('early', '-')}, 赛道风口={comp.get('tailwind', '-')}",
    ]
    return "\n".join(lines)


SYSTEM_PROMPT = (
    "你是开源技术投资分析师。请用简体中文写一段 2-4 句的"
    "「机会简报」，面向技术负责人，回答三点："
    "为什么值得关注、谁在做什么（结合语言/分类）、主要风险。"
    "编程语言名与技术专有名词（如 Python、Go、Rust、AI、MCP、RAG、LLM、"
    "GitHub star/fork）保持英文原样，不要翻译。只输出简报正文，"
    "不要标题、不要列表、不要多余解释。"
)


def generate_brief(
    candidate: dict[str, Any],
    provider: Any,
) -> str | None:
    """Ask the provider for one Chinese brief; ``None`` on any failure."""
    text = provider.complete(
        _build_prompt(candidate),
        system=SYSTEM_PROMPT,
        max_tokens=220,
        temperature=0.5,
    )
    if not text:
        return None
    # Collapse newlines/quotes into a single clean paragraph.
    cleaned = " ".join(line.strip() for line in text.splitlines() if line.strip())
    return cleaned or None


def generate_briefs(
    candidates: list[dict[str, Any]],
    *,
    provider: Any | None = None,
    out_path: Path = DEFAULT_OUT_PATH,
    limit: int = DEFAULT_BRIEF_LIMIT,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Generate/cache Chinese briefs for the top ``limit`` candidates.

    Idempotent and incremental: cached entries whose signal fingerprint is
    unchanged are skipped unless ``force``. Returns a stats dict. When
    ``dry_run`` is set no network call happens and nothing is written.
    """
    cache = load_briefs(out_path)
    targets = candidates[: max(0, limit)]

    pending = [
        c
        for c in targets
        if force
        or c["repo_full_name"] not in cache
        or cache[c["repo_full_name"]].get("fingerprint") != signal_fingerprint(c)
    ]

    stats: dict[str, Any] = {
        "targets": len(targets),
        "cached": len(cache),
        "pending": len(pending),
        "generated": 0,
        "skipped": 0,
        "cache_size": len(cache),
        "dry_run": dry_run,
    }

    if dry_run or not pending:
        return stats

    if provider is None:
        from radar.analysis.ai_provider import GroqProvider

        provider = GroqProvider()

    # Groq free tier is ~1-2 RPM, so serialize and flush after every single
    # success — a rate-limit or crash mid-run keeps everything already written.
    for c in pending:
        text = generate_brief(c, provider)
        if not text:
            stats["skipped"] += 1
            continue
        cache[c["repo_full_name"]] = {
            "text": text,
            "tier": c.get("tier", ""),
            "fingerprint": signal_fingerprint(c),
            "generated_at": datetime.now(tz=UTC).isoformat(),
        }
        save_briefs(out_path, cache)
        stats["generated"] += 1
        logger.info("briefed %s (%d/%d pending)", c["repo_full_name"],
                     stats["generated"], len(pending))

    stats["cache_size"] = len(cache)
    return stats


def merge_briefs_into(
    candidates: list[dict[str, Any]],
    briefs: dict[str, Any],
) -> list[dict[str, Any]]:
    """Attach ``brief_zh`` to each candidate in place (cache hit or template).

    Used by the export pipeline so ``opportunities.json`` carries a ready-to-
    render Chinese note per surfaced repo — AI text when available, otherwise
    the deterministic template so the card is never empty.
    """
    for c in candidates:
        entry = briefs.get(c["repo_full_name"])
        if isinstance(entry, dict) and entry.get("text"):
            c["brief_zh"] = entry["text"]
            c["brief_source"] = "groq"
        else:
            c["brief_zh"] = template_brief(c)
            c["brief_source"] = "template"
    return candidates


# ── Daily digest helpers (pure data; card building stays in the CLI) ──

def load_digest_state(path: Path = DEFAULT_DIGEST_STATE_PATH) -> dict[str, Any]:
    """Read the previous digest snapshot ({repo_full_name: tier})."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        tiers = data.get("tiers") if isinstance(data, dict) else None
        return tiers if isinstance(tiers, dict) else {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("digest state at %s unreadable (%s)", path, exc)
        return {}


def save_digest_state(
    candidates: list[dict[str, Any]],
    path: Path = DEFAULT_DIGEST_STATE_PATH,
) -> None:
    """Persist the current tiers so the next run can detect new / upgrades."""
    tiers = {c["repo_full_name"]: c.get("tier", "") for c in candidates}
    payload = {"updated_at": datetime.now(tz=UTC).isoformat(), "tiers": tiers}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def select_digest_candidates(
    candidates: list[dict[str, Any]],
    prev_tiers: dict[str, Any],
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """Return newly-surfaced or tier-upgraded candidates, best-first.

    A repo counts as *new* when absent from the previous snapshot and *upgraded*
    when its tier rank rose. Each result is annotated with ``digest_kind``
    ("new" | "upgraded"). When nothing changed, an empty list is returned.
    """
    picked: list[dict[str, Any]] = []
    for c in candidates:
        name = c["repo_full_name"]
        cur_rank = TIER_RANK.get(c.get("tier", ""), 0)
        prev_tier = prev_tiers.get(name)
        if prev_tier is None:
            c["digest_kind"] = "new"
            picked.append(c)
        elif cur_rank > TIER_RANK.get(prev_tier, 0):
            c["digest_kind"] = "upgraded"
            picked.append(c)
    picked.sort(key=lambda c: c.get("opportunity_score", 0), reverse=True)
    return picked[:top_n]
