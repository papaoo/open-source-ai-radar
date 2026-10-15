"""Tests for the build-time translation subsystem (providers, cache, driver).

No real network calls are made — httpx is patched and the driver is exercised
through a fake provider. Covers: disk cache round-trips, incremental/pending
selection, dry-run/limit/force behavior, Google response parsing and provider
resolution.
"""

import json

import httpx

from radar.translations import collect_descriptions, translate_descriptions
from radar.translations.providers import (
    DeepLTranslator,
    GoogleWebTranslator,
    GroqTranslator,
    get_provider,
)
from radar.translations.store import load_cache, save_cache


class FakeTranslator:
    name = "fake"

    def __init__(self):
        self.seen = []

    def is_available(self):
        return True

    def translate(self, texts, target="zh-CN"):
        batch = list(texts)
        self.seen.append(batch)
        return {t: f"译::{t}" for t in batch}


# ── store ──────────────────────────────────────────────────────────────
def test_load_cache_missing_returns_empty(tmp_path):
    assert load_cache(tmp_path / "nope.json") == {}


def test_load_cache_corrupt_returns_empty(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert load_cache(p) == {}


def test_save_then_load_roundtrip(tmp_path):
    p = tmp_path / "sub" / "cache.json"
    save_cache(p, {"hello": "你好", "world": "世界"})
    assert load_cache(p) == {"hello": "你好", "world": "世界"}
    assert not p.with_suffix(p.suffix + ".tmp").exists()  # atomic temp cleaned up


# ── collect_descriptions ───────────────────────────────────────────────
def test_collect_descriptions_dedupes_and_trims(tmp_path):
    idx = tmp_path / "index.json"
    idx.write_text(
        json.dumps(
            {
                "projects": [
                    {"description": "Alpha", "radar_score": 10},
                    {"description": "Alpha", "radar_score": 5},
                    {"description": "  Beta  ", "radar_score": 1},
                    {"description": "", "radar_score": 99},
                    {"description": None, "radar_score": 99},
                    {},
                ]
            }
        ),
        encoding="utf-8",
    )
    # de-duped + trimmed, ordered by radar score (highest first)
    assert collect_descriptions(idx) == ["Alpha", "Beta"]


def test_collect_descriptions_orders_by_score(tmp_path):
    idx = tmp_path / "index.json"
    idx.write_text(
        json.dumps(
            {
                "projects": [
                    {"description": "low", "radar_score": 1},
                    {"description": "high", "radar_score": 90},
                    {"description": "mid", "radar_score": 50},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert collect_descriptions(idx) == ["high", "mid", "low"]


def test_collect_descriptions_missing_file(tmp_path):
    assert collect_descriptions(tmp_path / "none.json") == []


# ── driver ─────────────────────────────────────────────────────────────
def _make_index(tmp_path, descs):
    idx = tmp_path / "index.json"
    idx.write_text(
        json.dumps({"projects": [{"description": d} for d in descs]}), encoding="utf-8"
    )
    return idx


def test_translate_incremental_skips_cached(tmp_path):
    idx = _make_index(tmp_path, ["one", "two", "three"])
    out = tmp_path / "cache.json"
    save_cache(out, {"one": "1"})

    fake = FakeTranslator()
    stats = translate_descriptions(
        index_path=idx, out_path=out, provider=fake, limit=None, dry_run=False
    )
    assert stats["translated"] == 2  # only "two" and "three"
    assert set(fake.seen[0]) == {"three", "two"}  # cached "one" skipped
    assert load_cache(out) == {"one": "1", "two": "译::two", "three": "译::three"}


def test_translate_dry_run_writes_nothing(tmp_path):
    idx = _make_index(tmp_path, ["a", "b"])
    out = tmp_path / "cache.json"
    fake = FakeTranslator()
    stats = translate_descriptions(index_path=idx, out_path=out, provider=fake, dry_run=True)
    assert stats["pending"] == 2
    assert stats["dry_run"] is True
    assert fake.seen == []  # never called
    assert not out.exists()


def test_translate_limit_and_force(tmp_path):
    idx = _make_index(tmp_path, ["x", "y", "z"])
    out = tmp_path / "cache.json"
    save_cache(out, {"x": "译::x"})

    # limit caps pending
    fake = FakeTranslator()
    stats = translate_descriptions(index_path=idx, out_path=out, provider=fake, limit=1)
    assert stats["translated"] == 1

    # force re-translates everything incl. cached
    fake2 = FakeTranslator()
    stats2 = translate_descriptions(index_path=idx, out_path=out, provider=fake2, force=True)
    assert stats2["pending"] == 3


def test_translate_empty_pending_shortcircuit(tmp_path):
    idx = _make_index(tmp_path, ["only"])
    out = tmp_path / "cache.json"
    save_cache(out, {"only": "译::only"})
    stats = translate_descriptions(index_path=idx, out_path=out, provider=FakeTranslator())
    assert stats["pending"] == 0
    assert stats["translated"] == 0


# ── google provider parsing ────────────────────────────────────────────
def test_google_translator_parses_segments(monkeypatch):
    captured = {}

    class Resp:
        status_code = 200

        def json(self):
            # segmented response should be concatenated
            return [[["你", "he"], ["好", "llo"]], ["en"]]

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return Resp()

    monkeypatch.setattr(httpx, "get", fake_get)
    t = GoogleWebTranslator(max_workers=2)
    out = t.translate(["hello"])
    assert out == {"hello": "你好"}
    assert captured["params"]["tl"] == "zh-CN"
    assert captured["params"]["q"] == "hello"


def test_google_translator_skips_on_error(monkeypatch):
    def boom(url, params=None, timeout=None):
        raise httpx.ConnectError("no net")

    monkeypatch.setattr(httpx, "get", boom)
    t = GoogleWebTranslator(max_workers=2)
    assert t.translate(["hello"]) == {}


def test_google_translator_non_200_returns_nothing(monkeypatch):
    class Resp:
        status_code = 429

        def json(self):
            return None

    monkeypatch.setattr(httpx, "get", lambda *a, **k: Resp())
    # retries=1 so the rate-limit backoff doesn't sleep in tests
    t = GoogleWebTranslator(max_workers=2, retries=1)
    assert t.translate(["hello"]) == {}


# ── provider resolution ────────────────────────────────────────────────
def test_get_provider_defaults_to_google(monkeypatch):
    monkeypatch.delenv("DEEPL_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEYS", raising=False)
    assert isinstance(get_provider("auto"), GoogleWebTranslator)


def test_get_provider_prefers_deepl_when_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEYS", raising=False)
    monkeypatch.setenv("DEEPL_API_KEY", "abc123:fx")
    assert isinstance(get_provider("auto"), DeepLTranslator)


def test_get_provider_prefers_groq_when_keyed(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEYS", "keyA,keyB")
    provider = get_provider("auto")
    assert isinstance(provider, GroqTranslator)
    assert provider.is_available()


def test_deepl_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("DEEPL_API_KEY", raising=False)
    assert DeepLTranslator().is_available() is False


# ── groq provider ──────────────────────────────────────────────────────
class _GroqResp:
    def __init__(self, content, status=200):
        self.status_code = status
        self._content = content

    def raise_for_status(self):
        if self.status_code != 200:
            raise httpx.HTTPStatusError("rate limited", request=None, response=None)

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def test_groq_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEYS", raising=False)
    assert GroqTranslator().is_available() is False
    # no key → translate is a no-op, never raises
    assert GroqTranslator().translate(["hello"]) == {}


def test_groq_translates_numbered_batch(monkeypatch):
    seen = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen["auth"] = headers["Authorization"]
        seen["payload"] = json
        # model echoes two tab-separated translations
        return _GroqResp("0\t你好\n1\t世界")

    monkeypatch.setattr(httpx, "post", fake_post)
    t = GroqTranslator(api_keys="k1,k2", min_interval=0)
    out = t.translate(["hello", "world"])
    assert out == {"hello": "你好", "world": "世界"}
    assert seen["auth"].startswith("Bearer ")
    # system prompt names the target language
    assert "Simplified Chinese" in seen["payload"]["messages"][0]["content"]


def test_groq_rotates_keys_across_batches(monkeypatch):
    used = []

    def fake_post(url, headers=None, json=None, timeout=None):
        used.append(headers["Authorization"])
        return _GroqResp("0\t译")

    monkeypatch.setattr(httpx, "post", fake_post)
    t = GroqTranslator(api_keys="A,B", batch_size=1, min_interval=0)
    t.translate(["one", "two"])
    assert used == ["Bearer A", "Bearer B"]  # round-robin per request


def test_groq_skips_batch_on_rate_limit(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return _GroqResp("", status=429)

    monkeypatch.setattr(httpx, "post", fake_post)
    t = GroqTranslator(api_keys="k1", min_interval=0)
    # 429 raises inside the batch and is swallowed so the run keeps going
    assert t.translate(["hello"]) == {}


def test_groq_parse_tolerates_alternate_formats():
    chunk = ["a", "b", "c"]
    content = "0: 甲\n1. 乙\ngarbage line\n2\t丙"
    assert GroqTranslator._parse(content, chunk) == {"a": "甲", "b": "乙", "c": "丙"}
