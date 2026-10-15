"""Opportunity Index Engine — surfaces under-priced, early, sustainable bets.

Distinct from the other scores:
- ``radar_score``    — how important is this RIGHT NOW.
- ``breakout_score`` — how close is it to exploding.
- ``opportunity_score`` — strong leading indicators + sustainability, but NOT
  yet priced-in by the mainstream. Emphasizes earliness, contributor pull
  (a leading signal nobody else uses) and controllable risk.

Everything is computed from the existing SQLite tables — zero extra GitHub API
calls, so it never touches the ``config/scale.yml`` rate budget.

Components (each 0-100), weighted into ``opportunity_score``:
1. Early            (20%) — 100 - log(stars) percentile within its category.
2. Momentum         (20%) — velocity + normalized 7d star growth rate.
3. Acceleration     (15%) — mirrors breakout: (accel - 0.5) * 66.7.
4. Contributor pull (15%) — contributors_7d + forks_7d (fallback + neutral).
5. Viability        (15%) — health + bus factor + license + release cadence.
6. Tailwind         (10%) — category momentum score.
7. Whitespace        (5%) — low tracked count but high category velocity.

Guardrails keep this an *opportunity* (not fame): health >= 50 and
stars <= 200000. Tiers: >=70 blue_ocean, 55-69 high_potential, 40-54 watch.
"""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime
from typing import Any

from radar.storage.database import Database

logger = logging.getLogger(__name__)

#: Component weights (sum = 1.0).
WEIGHTS: dict[str, float] = {
    "early": 0.20,
    "momentum": 0.20,
    "acceleration": 0.15,
    "contributor_pull": 0.15,
    "viability": 0.15,
    "tailwind": 0.10,
    "whitespace": 0.05,
}

#: Adoption guardrails — an opportunity is early, not already mainstream.
MIN_HEALTH = 50.0
MAX_STARS = 200000

#: Category scarcity normalization for the whitespace component.
WHITESPACE_TRACKED_MAX = 200

TIER_BLUE_OCEAN = "blue_ocean"
TIER_HIGH_POTENTIAL = "high_potential"
TIER_WATCH = "watch"


def _percentile_rank(value: float, sorted_values: list[float]) -> float:
    """Percentile rank (0-100). ``sorted_values`` must be ascending."""
    n = len(sorted_values)
    if n == 0:
        return 0.0
    lo, hi = 0, n
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_values[mid] < value:
            lo = mid + 1
        else:
            hi = mid
    return (lo / n) * 100


def _log_scale(value: float) -> float:
    return math.log(value + 1) if value > 0 else 0.0


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


class OpportunityEngine:
    """Ranks repositories by an actionable opportunity score."""

    #: Licenses safe for adopters (mirrors ScoringEngine.SAFE_LICENSES).
    SAFE_LICENSES: frozenset[str] = frozenset({
        "MIT", "Apache-2.0", "Apache-2.0 WITH LLVM-exception", "BSD-2-Clause",
        "BSD-3-Clause", "BSD-3-Clause-Clear", "ISC", "MPL-2.0", "Unlicense",
        "CC0-1.0", "CC-BY-4.0", "Zlib", "0BSD", "BSL-1.0",
        "GPL-2.0", "GPL-2.0-only", "GPL-2.0-or-later",
        "GPL-3.0", "GPL-3.0-only", "GPL-3.0-or-later",
        "LGPL-2.1", "LGPL-2.1-only", "LGPL-2.1-or-later",
        "LGPL-3.0", "LGPL-3.0-only", "LGPL-3.0-or-later",
        "AGPL-3.0", "AGPL-3.0-only", "AGPL-3.0-or-later",
        "EPL-1.0", "EPL-2.0", "CDDL-1.0", "CECILL-2.1", "EUPL-1.2",
    })

    def __init__(self, db: Database) -> None:
        self.db = db

    # ── Public API ──────────────────────────────────────────────────

    def compute_opportunities(
        self,
        limit: int = 50,
        min_score: float = 40.0,
    ) -> list[dict[str, Any]]:
        """Return repos ranked by opportunity score (>= ``min_score``)."""
        rows = self._fetch_signals()
        if not rows:
            return []

        cat_stats = self._compute_category_stats(rows)
        category_ctx = self._load_category_context()

        candidates: list[dict[str, Any]] = []
        for d in rows:
            components = self._score_components(d, cat_stats, category_ctx)
            score = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)
            score = _clamp(score)

            if score < min_score:
                continue

            candidates.append({
                "repo_full_name": d["full_name"],
                "url": d.get("url"),
                "language": d.get("language"),
                "category": d.get("category") or "Unknown",
                "sub_category": d.get("sub_category") or "",
                "stars": d.get("stars", 0),
                "forks": d.get("forks", 0),
                "radar_score": round(d.get("radar_score", 0), 1),
                "velocity": round(d.get("velocity", 0), 1),
                "health": round(d.get("health", 0), 1),
                "stars_7d": d.get("stars_7d", 0),
                "star_growth_rate_7d": round(d.get("star_growth_rate_7d", 0), 1),
                "star_growth_acceleration": round(
                    d.get("star_growth_acceleration", 1.0), 2
                ),
                "forks_7d": d.get("forks_7d", 0),
                "contributors_7d": d.get("contributors_7d", 0),
                "freshness": round(d.get("freshness_score", 0) * 100, 0),
                "opportunity_score": round(score, 1),
                "tier": self._tier_for(score),
                "components": {k: round(v, 1) for k, v in components.items()},
            })

        candidates.sort(key=lambda c: c["opportunity_score"], reverse=True)
        logger.info(f"Computed {len(candidates)} opportunity candidates")
        return candidates[:limit]

    def get_whitespace_categories(self) -> list[dict[str, Any]]:
        """Categories with high momentum but few tracked repos."""
        category_ctx = self._load_category_context()
        result = [
            {
                "category": cat,
                "total_tracked": ctx["total_tracked"],
                "avg_velocity": round(ctx["avg_velocity"], 1),
                "momentum_score": round(ctx["momentum_score"], 1),
                "trend": ctx["trend"],
                "whitespace_score": round(self._whitespace_score(ctx), 1),
            }
            for cat, ctx in category_ctx.items()
        ]
        result.sort(key=lambda c: c["whitespace_score"], reverse=True)
        return result

    def get_opportunities_summary(
        self,
        limit: int = 50,
        min_score: float = 40.0,
    ) -> dict[str, Any]:
        """Bundle candidates + whitespace for API/export payloads."""
        candidates = self.compute_opportunities(limit, min_score)
        return {
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "total_candidates": len(candidates),
            "candidates": candidates,
            "whitespace": self.get_whitespace_categories(),
        }

    # ── Data loading ────────────────────────────────────────────────

    def _fetch_signals(self) -> list[dict[str, Any]]:
        """Single JOIN across scores + growth + analysis, applying guardrails."""
        with self.db._conn() as conn:
            rows = conn.execute(
                """SELECT
                    r.full_name, r.stars, r.forks, r.language, r.url,
                    r.license, r.created_at, r.pushed_at,
                    s.radar_score, s.velocity, s.health,
                    g.stars_7d, g.stars_30d,
                    g.star_growth_rate_7d, g.star_growth_acceleration,
                    g.forks_7d, g.contributors_7d, g.freshness_score,
                    a.category, a.sub_category, a.maturity
                FROM repositories r
                JOIN scores s ON r.full_name = s.repo_full_name
                    AND s.timestamp = (SELECT MAX(timestamp) FROM scores)
                LEFT JOIN growth_metrics g ON r.full_name = g.repo_full_name
                    AND g.timestamp = (SELECT MAX(timestamp) FROM growth_metrics)
                LEFT JOIN ai_analysis a ON r.full_name = a.repo_full_name
                WHERE r.stars <= ?
                  AND s.health >= ?""",
                (MAX_STARS, MIN_HEALTH),
            ).fetchall()
            return [dict(r) for r in rows]

    def _load_category_context(self) -> dict[str, dict[str, Any]]:
        """Latest category_momentum row per category (tailwind + whitespace)."""
        with self.db._conn() as conn:
            rows = conn.execute(
                """SELECT cm.category, cm.total_tracked, cm.avg_velocity,
                          cm.momentum_score, cm.trend
                FROM category_momentum cm
                INNER JOIN (
                    SELECT category, MAX(timestamp) as max_ts
                    FROM category_momentum
                    GROUP BY category
                ) latest ON cm.category = latest.category
                    AND cm.timestamp = latest.max_ts"""
            ).fetchall()
        return {
            r["category"]: {
                "total_tracked": r["total_tracked"] or 0,
                "avg_velocity": r["avg_velocity"] or 0.0,
                "momentum_score": r["momentum_score"] or 0.0,
                "trend": r["trend"] or "stable",
            }
            for r in rows
        }

    def _compute_category_stats(
        self, rows: list[dict[str, Any]]
    ) -> dict[str, list[float]]:
        """Sorted log(stars) lists per category for the earliness percentile."""
        by_cat: dict[str, list[float]] = {}
        for d in rows:
            cat = d.get("category") or "Unknown"
            by_cat.setdefault(cat, []).append(_log_scale(float(d.get("stars", 0))))
        return {cat: sorted(vals) for cat, vals in by_cat.items()}

    # ── Scoring ─────────────────────────────────────────────────────

    def _score_components(
        self,
        repo: dict[str, Any],
        cat_stats: dict[str, list[float]],
        category_ctx: dict[str, dict[str, Any]],
    ) -> dict[str, float]:
        cat = repo.get("category") or "Unknown"

        # 1. Early — low log(stars) percentile within category = high score.
        log_stars = _log_scale(float(repo.get("stars", 0)))
        peers = cat_stats.get(cat, [])
        # too few peers to judge earliness → neutral 50
        early = (
            _clamp(100 - _percentile_rank(log_stars, peers))
            if len(peers) >= 3
            else 50.0
        )

        # 2. Momentum — blend velocity and 7d star growth rate.
        velocity_score = _clamp(repo.get("velocity", 0))
        growth_score = _clamp(repo.get("star_growth_rate_7d", 0) * 15)
        momentum = velocity_score * 0.5 + growth_score * 0.5

        # 3. Acceleration — mirror breakout mapping.
        accel = repo.get("star_growth_acceleration", 1.0)
        acceleration = _clamp((accel - 0.5) * 66.7)

        # 4. Contributor pull — leading signal, with fallback + neutral.
        contributor_pull = self._contributor_pull_score(repo)

        # 5. Viability — health + bus factor + license + release cadence.
        viability = self._viability_score(repo)

        # 6. Tailwind — category momentum score.
        ctx = category_ctx.get(cat)
        tailwind = _clamp(ctx["momentum_score"]) if ctx else 50.0

        # 7. Whitespace — high category velocity, few tracked repos.
        whitespace = self._whitespace_score(ctx) if ctx else 50.0

        return {
            "early": early,
            "momentum": momentum,
            "acceleration": acceleration,
            "contributor_pull": contributor_pull,
            "viability": viability,
            "tailwind": tailwind,
            "whitespace": whitespace,
        }

    def _contributor_pull_score(self, repo: dict[str, Any]) -> float:
        contributors_7d = repo.get("contributors_7d") or 0
        forks_7d = repo.get("forks_7d") or 0
        contrib_score = _clamp(contributors_7d * 12)
        fork_score = _clamp(forks_7d * 6)

        if contributors_7d > 0:
            return contrib_score * 0.6 + fork_score * 0.4
        if forks_7d > 0:
            return fork_score  # fallback when contributors not collected
        return 50.0  # both zero / missing — neutral, don't penalize

    def _viability_score(self, repo: dict[str, Any]) -> float:
        health_score = _clamp(repo.get("health", 0))
        license_component = self._license_score(repo.get("license"))
        cadence = _clamp((repo.get("freshness_score", 0) or 0) * 100)
        bus = self._bus_factor_score(repo.get("contributors") or 0)
        return (
            health_score * 0.40
            + license_component * 0.20
            + cadence * 0.20
            + bus * 0.20
        )

    def _bus_factor_score(self, contributors: int) -> float:
        """Maintainer-risk proxy — same thresholds as ScoringEngine.

        Without snapshot contributor counts we score mid (neutral) rather than
        penalizing, since ``contributors`` is not in the signals join.
        """
        if contributors == 0:
            return 60.0
        if contributors >= 25:
            return 95.0
        if contributors >= 10:
            return 85.0
        if contributors >= 5:
            return 70.0
        if contributors >= 2:
            return 50.0
        return 20.0

    def _license_score(self, license_id: str | None) -> float:
        license_id = (license_id or "").strip()
        if not license_id:
            return 30.0
        return 90.0 if license_id in self.SAFE_LICENSES else 60.0

    def _whitespace_score(self, ctx: dict[str, Any]) -> float:
        velocity = _clamp(ctx.get("avg_velocity", 0))
        tracked = ctx.get("total_tracked", 0)
        scarcity = _clamp(
            100 * (1 - min(1.0, tracked / WHITESPACE_TRACKED_MAX))
        )
        return velocity * 0.6 + scarcity * 0.4

    @staticmethod
    def _tier_for(score: float) -> str:
        if score >= 70:
            return TIER_BLUE_OCEAN
        if score >= 55:
            return TIER_HIGH_POTENTIAL
        return TIER_WATCH
