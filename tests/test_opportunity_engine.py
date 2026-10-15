"""Tests for the Opportunity Index engine.

Covers: tier boundaries, adoption guardrails (health / stars), the
contributors_7d fallback, whitespace-category detection, and end-to-end
ordering / min_score / limit filtering of ``compute_opportunities``.
"""

from __future__ import annotations

import pytest

from radar.analysis.opportunity_engine import (
    TIER_BLUE_OCEAN,
    TIER_HIGH_POTENTIAL,
    TIER_WATCH,
    OpportunityEngine,
)
from radar.storage.database import Database

TS = "2026-01-01T00:00:00+00:00"  # fixed so MAX(timestamp) matches every row


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "radar.db")


@pytest.fixture
def engine(db):
    return OpportunityEngine(db)


def _seed(
    db,
    full_name,
    *,
    stars=1000,
    health=60.0,
    velocity=60.0,
    radar=60.0,
    category="AI Agents",
    license="MIT",
    stars_7d=100,
    rate_7d=5.0,
    accel=1.0,
    forks_7d=10,
    contributors_7d=5,
    freshness=1.0,
):
    """Insert one fully-linked repo (repo + score + growth + analysis)."""
    db.upsert_repo({
        "full_name": full_name,
        "url": f"https://github.com/{full_name}",
        "stars": stars,
        "forks": forks_7d * 10,
        "license": license,
        "language": "Python",
        "created_at": "2025-06-01T00:00:00Z",
        "pushed_at": "2025-12-30T00:00:00Z",
    })
    db.save_score({
        "repo_full_name": full_name,
        "timestamp": TS,
        "velocity": velocity,
        "health": health,
        "radar_score": radar,
    })
    db.save_growth({
        "repo_full_name": full_name,
        "timestamp": TS,
        "stars_7d": stars_7d,
        "star_growth_rate_7d": rate_7d,
        "star_growth_acceleration": accel,
        "forks_7d": forks_7d,
        "contributors_7d": contributors_7d,
        "freshness_score": freshness,
    })
    db.save_analysis({
        "repo_full_name": full_name,
        "timestamp": TS,
        "category": category,
    })


def _seed_momentum(db, category, *, tracked, velocity, momentum, trend="rising"):
    with db._conn() as conn:
        conn.execute(
            """INSERT INTO category_momentum
                (category, timestamp, total_tracked, avg_velocity,
                 momentum_score, trend)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (category, TS, tracked, velocity, momentum, trend),
        )


class TestTierBoundaries:
    def test_blue_ocean(self, engine):
        assert engine._tier_for(70) == TIER_BLUE_OCEAN
        assert engine._tier_for(100) == TIER_BLUE_OCEAN

    def test_high_potential(self, engine):
        assert engine._tier_for(55) == TIER_HIGH_POTENTIAL
        assert engine._tier_for(69.9) == TIER_HIGH_POTENTIAL

    def test_watch(self, engine):
        assert engine._tier_for(40) == TIER_WATCH
        assert engine._tier_for(54.9) == TIER_WATCH


class TestContributorPull:
    def test_prefers_contributors(self, engine):
        # both saturate to 100 → pull = 100
        repo = {"contributors_7d": 20, "forks_7d": 30}
        assert engine._contributor_pull_score(repo) == pytest.approx(100.0)

    def test_contributors_weighted_over_forks(self, engine):
        # contributors drives 60%, forks 40%
        repo = {"contributors_7d": 10, "forks_7d": 10}
        # contrib=100, fork=60 → 0.6*100 + 0.4*60 = 84
        assert engine._contributor_pull_score(repo) == pytest.approx(84.0)

    def test_falls_back_to_forks(self, engine):
        # contributors missing/0 → use forks score only
        repo = {"contributors_7d": 0, "forks_7d": 5}
        assert engine._contributor_pull_score(repo) == pytest.approx(30.0)

    def test_neutral_when_both_zero(self, engine):
        assert engine._contributor_pull_score(
            {"contributors_7d": 0, "forks_7d": 0}
        ) == 50.0

    def test_none_values_do_not_crash(self, engine):
        assert engine._contributor_pull_score(
            {"contributors_7d": None, "forks_7d": None}
        ) == 50.0


class TestGuardrails:
    def test_low_health_excluded(self, db, engine):
        _seed(db, "weak/repo", health=20.0)
        names = [c["repo_full_name"] for c in engine.compute_opportunities()]
        assert "weak/repo" not in names

    def test_mainstream_stars_excluded(self, db, engine):
        _seed(db, "huge/repo", stars=250000, health=80.0)
        names = [c["repo_full_name"] for c in engine.compute_opportunities()]
        assert "huge/repo" not in names

    def test_boundary_health_kept(self, db, engine):
        _seed(db, "edge/repo", health=50.0, velocity=90, rate_7d=10, accel=2.0)
        names = [c["repo_full_name"] for c in engine.compute_opportunities()]
        assert "edge/repo" in names


class TestComputeOpportunities:
    def test_strong_repo_is_blue_ocean(self, db, engine):
        _seed(
            db, "star/rise", stars=1200, health=80, velocity=90,
            rate_7d=12, accel=2.0, forks_7d=25, contributors_7d=12,
        )
        results = engine.compute_opportunities()
        assert results
        top = results[0]
        assert top["repo_full_name"] == "star/rise"
        assert top["tier"] == TIER_BLUE_OCEAN
        assert top["tier"] == engine._tier_for(top["opportunity_score"])
        # component transparency present
        assert set(top["components"]) == {
            "early", "momentum", "acceleration", "contributor_pull",
            "viability", "tailwind", "whitespace",
        }

    def test_sorted_desc_and_min_score(self, db, engine):
        _seed(db, "a/one", velocity=95, rate_7d=15, accel=3.0,
              contributors_7d=20, forks_7d=30, health=85)
        _seed(db, "b/two", velocity=60, rate_7d=3, accel=1.0,
              contributors_7d=3, forks_7d=5, health=55)
        results = engine.compute_opportunities(min_score=40)
        scores = [c["opportunity_score"] for c in results]
        assert scores == sorted(scores, reverse=True)
        assert all(s >= 40 for s in scores)

    def test_limit_applied(self, db, engine):
        for i in range(5):
            _seed(db, f"repo/{i}", velocity=80, rate_7d=8, accel=1.5,
                  contributors_7d=8, forks_7d=15)
        results = engine.compute_opportunities(limit=3)
        assert len(results) == 3

    def test_empty_db_returns_empty(self, engine):
        assert engine.compute_opportunities() == []


class TestWhitespaceCategories:
    def test_orders_scarce_fast_first(self, db, engine):
        _seed_momentum(db, "Frontier", tracked=5, velocity=90, momentum=80)
        _seed_momentum(db, "Saturated", tracked=200, velocity=20, momentum=30)
        cats = engine.get_whitespace_categories()
        assert cats[0]["category"] == "Frontier"
        assert cats[0]["whitespace_score"] > cats[-1]["whitespace_score"]

    def test_includes_expected_fields(self, db, engine):
        _seed_momentum(db, "Frontier", tracked=10, velocity=70, momentum=60)
        cats = engine.get_whitespace_categories()
        row = cats[0]
        assert {"category", "total_tracked", "avg_velocity",
                "momentum_score", "trend", "whitespace_score"} <= set(row)


class TestViability:
    def test_safe_license_outranks_missing(self, engine):
        safe = engine._viability_score(
            {"health": 60, "license": "MIT", "freshness_score": 1.0}
        )
        missing = engine._viability_score(
            {"health": 60, "license": None, "freshness_score": 1.0}
        )
        assert safe > missing
