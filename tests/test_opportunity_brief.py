"""Tests for the optional P3 opportunity-brief + digest layer."""

from __future__ import annotations

from pathlib import Path

from radar.analysis import opportunity_brief as ob


def _candidate(name: str = "acme/widget", tier: str = "high_potential", **over):
    base = {
        "repo_full_name": name,
        "category": "MCP",
        "sub_category": "",
        "language": "Python",
        "stars": 1200,
        "forks": 90,
        "velocity": 62.0,
        "health": 71.0,
        "stars_7d": 340,
        "star_growth_acceleration": 2.1,
        "contributors_7d": 12,
        "forks_7d": 30,
        "opportunity_score": 63.0,
        "tier": tier,
        "components": {"early": 80.0, "tailwind": 55.0},
    }
    base.update(over)
    return base


class _FakeProvider:
    """Stands in for GroqProvider; records prompts, returns canned text."""

    def __init__(self, reply: str | None = "这是中文简报。Python 与 MCP 保持英文。"):
        self.reply = reply
        self.calls: list[str] = []

    def complete(self, prompt, *, system="", max_tokens=0, temperature=0.0):
        self.calls.append(prompt)
        return self.reply


class TestFingerprint:
    def test_stable_for_identical_signals(self):
        assert ob.signal_fingerprint(_candidate()) == ob.signal_fingerprint(_candidate())

    def test_changes_with_tier(self):
        a = ob.signal_fingerprint(_candidate(tier="watch"))
        b = ob.signal_fingerprint(_candidate(tier="blue_ocean"))
        assert a != b

    def test_ignores_minor_jitter(self):
        # stars within the same 500-bucket and accel within 0.1 rounding → same key.
        a = ob.signal_fingerprint(_candidate(stars=1200, star_growth_acceleration=2.14))
        b = ob.signal_fingerprint(_candidate(stars=1210, star_growth_acceleration=2.13))
        assert a == b


class TestTemplateBrief:
    def test_contains_repo_and_tier_zh(self):
        text = ob.template_brief(_candidate())
        assert "acme/widget" in text
        assert "高潜力" in text

    def test_preserves_proper_nouns(self):
        # Language / category are kept as-is (English), never translated.
        text = ob.template_brief(_candidate(language="Go", category="RAG"))
        assert "Go" in text
        assert "RAG" in text


class TestGenerateBriefs:
    def test_dry_run_does_not_write(self, tmp_path: Path):
        out = tmp_path / "briefs.json"
        stats = ob.generate_briefs(
            [_candidate()], provider=_FakeProvider(), out_path=out, dry_run=True
        )
        assert stats["dry_run"] is True
        assert stats["generated"] == 0
        assert not out.exists()

    def test_generates_and_persists(self, tmp_path: Path):
        out = tmp_path / "briefs.json"
        prov = _FakeProvider()
        stats = ob.generate_briefs([_candidate("a/b")], provider=prov, out_path=out)
        assert stats["generated"] == 1
        cache = ob.load_briefs(out)
        assert cache["a/b"]["text"].startswith("这是中文简报")
        assert cache["a/b"]["fingerprint"] == ob.signal_fingerprint(_candidate("a/b"))

    def test_incremental_skips_cached(self, tmp_path: Path):
        out = tmp_path / "briefs.json"
        ob.generate_briefs([_candidate("a/b")], provider=_FakeProvider(), out_path=out)
        prov2 = _FakeProvider()
        stats = ob.generate_briefs([_candidate("a/b")], provider=prov2, out_path=out)
        assert stats["pending"] == 0
        assert stats["generated"] == 0
        assert prov2.calls == []  # no network for already-cached repo

    def test_rebriefs_when_signals_change(self, tmp_path: Path):
        out = tmp_path / "briefs.json"
        ob.generate_briefs(
            [_candidate("a/b", tier="watch")], provider=_FakeProvider(), out_path=out
        )
        prov = _FakeProvider()
        stats = ob.generate_briefs(
            [_candidate("a/b", tier="blue_ocean")], provider=prov, out_path=out
        )
        assert stats["pending"] == 1
        assert len(prov.calls) == 1

    def test_skips_on_rate_limited_reply(self, tmp_path: Path):
        out = tmp_path / "briefs.json"
        prov = _FakeProvider(reply=None)  # simulate no key / 429
        stats = ob.generate_briefs([_candidate("a/b")], provider=prov, out_path=out)
        assert stats["generated"] == 0
        assert stats["skipped"] == 1
        assert ob.load_briefs(out) == {}


class TestMergeBriefs:
    def test_ai_hit_vs_template_fallback(self, tmp_path: Path):
        briefs = {"a/b": {"text": "AI 生成的中文简报", "tier": "watch"}}
        cands = [_candidate("a/b"), _candidate("c/d")]
        ob.merge_briefs_into(cands, briefs)
        assert cands[0]["brief_zh"] == "AI 生成的中文简报"
        assert cands[0]["brief_source"] == "groq"
        assert cands[1]["brief_source"] == "template"
        assert "c/d" in cands[1]["brief_zh"]


class TestDigestSelection:
    def test_new_repo(self):
        picked = ob.select_digest_candidates([_candidate("a/b")], prev_tiers={}, top_n=5)
        assert len(picked) == 1
        assert picked[0]["digest_kind"] == "new"

    def test_upgraded_tier(self):
        prev = {"a/b": "watch"}
        picked = ob.select_digest_candidates([_candidate("a/b", tier="blue_ocean")], prev)
        assert picked and picked[0]["digest_kind"] == "upgraded"

    def test_unchanged_not_picked(self):
        prev = {"a/b": "high_potential"}
        picked = ob.select_digest_candidates([_candidate("a/b", tier="high_potential")], prev)
        assert picked == []

    def test_downgraded_not_picked(self):
        prev = {"a/b": "blue_ocean"}
        picked = ob.select_digest_candidates([_candidate("a/b", tier="watch")], prev)
        assert picked == []

    def test_sorted_by_score_and_capped(self):
        prev: dict[str, str] = {}
        cands = [
            _candidate("x/1", opportunity_score=55.0),
            _candidate("x/2", opportunity_score=80.0),
            _candidate("x/3", opportunity_score=65.0),
        ]
        picked = ob.select_digest_candidates(cands, prev, top_n=2)
        assert [c["repo_full_name"] for c in picked] == ["x/2", "x/3"]


class TestDigestStateRoundTrip:
    def test_save_then_load(self, tmp_path: Path):
        state_path = tmp_path / ".state.json"
        cands = [_candidate("a/b", tier="watch"), _candidate("c/d", tier="blue_ocean")]
        ob.save_digest_state(cands, path=state_path)
        loaded = ob.load_digest_state(state_path)
        assert loaded == {"a/b": "watch", "c/d": "blue_ocean"}

    def test_load_missing_is_empty(self, tmp_path: Path):
        assert ob.load_digest_state(tmp_path / "nope.json") == {}


class TestGroqCompleteNoKey:
    def test_returns_none_without_keys(self, monkeypatch):
        from radar.analysis.ai_provider import GroqProvider

        monkeypatch.delenv("GROQ_API_KEYS", raising=False)
        provider = GroqProvider()
        assert provider.complete("hello", system="sys") is None
