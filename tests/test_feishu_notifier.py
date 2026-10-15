"""Tests for the Feishu group-bot notification module (delivery-only).

These cover the *plumbing*: signature correctness, payload shapes, response
handling, retry/rate-limit behavior and dry-run rendering. No real network calls
are made — ``httpx.post`` is patched.
"""

import base64
import hashlib
import hmac
import json

import pytest

import radar.notifications.feishu as feishu_mod
from radar.notifications import (
    NotificationPayload,
    build_default_payload,
    get_notifiers,
    load_notify_config,
)
from radar.notifications.feishu import FeishuBotNotifier, sign


class FakeResponse:
    def __init__(self, status_code=200, payload=None, raises_json=False):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"code": 0, "msg": "success"}
        self._raises_json = raises_json

    def json(self):
        if self._raises_json:
            raise ValueError("not json")
        return self._payload


@pytest.fixture
def notifier(tmp_path, monkeypatch):
    monkeypatch.setenv("FEISHU_WEBHOOK_URL", "https://open.feishu.cn/open-apis/bot/v2/hook/abc")
    monkeypatch.delenv("FEISHU_SECRET", raising=False)
    cfg = {
        "channels": {"feishu": {"enabled": True}},
        "rate_limit": {
            "state_path": str(tmp_path / "state.json"),
            "min_interval_seconds": 0,
            "daily_cap": 0,
        },
    }
    n = FeishuBotNotifier(cfg)
    n.backoff_base = 0.0  # keep retry tests fast
    return n


# ── signature ──────────────────────────────────────────────────────────
def test_sign_matches_documented_algorithm():
    secret, ts = "SECRET", 1700000000
    expected = base64.b64encode(
        hmac.new(f"{ts}\n{secret}".encode(), digestmod=hashlib.sha256).digest()
    ).decode()
    assert sign(secret, ts) == expected


def test_sign_is_deterministic_and_varies():
    assert sign("s", 1) == sign("s", 1)
    assert sign("s", 1) != sign("s", 2)
    assert sign("s", 1) != sign("t", 1)


# ── configuration gating ────────────────────────────────────────────────
def test_not_configured_without_webhook(monkeypatch, tmp_path):
    monkeypatch.delenv("FEISHU_WEBHOOK_URL", raising=False)
    n = FeishuBotNotifier(
        {
            "channels": {"feishu": {"enabled": True}},
            "rate_limit": {"state_path": str(tmp_path / "s.json")},
        }
    )
    assert n.is_configured() is False
    called = {"hit": False}

    def fake_post(*a, **k):
        called["hit"] = True
        return FakeResponse()

    monkeypatch.setattr(feishu_mod.httpx, "post", fake_post)
    res = n.send(NotificationPayload(text="hi"))
    assert res.skipped is True
    assert res.ok is False
    assert called["hit"] is False  # never touches network when unconfigured


# ── payload shapes ──────────────────────────────────────────────────────
def test_text_payload_shape(notifier):
    body = notifier._build_body(NotificationPayload(text="hello"))
    assert body["msg_type"] == "text"
    assert body["content"] == {"text": "hello"}
    assert "sign" not in body  # no secret configured


def test_card_payload_shape(notifier):
    payload = build_default_payload("https://example.com")
    body = notifier._build_body(payload)
    assert body["msg_type"] == "interactive"
    assert "card" in body and body["card"]["header"]["title"]["content"]


def test_post_payload_shape(notifier):
    post_body = {"zh_cn": {"title": "T", "content": [[{"tag": "text", "text": "x"}]]}}
    body = notifier._build_body(NotificationPayload(post=post_body))
    assert body["msg_type"] == "post"
    assert body["content"]["post"] == post_body


def test_sign_added_when_secret_present(notifier, monkeypatch):
    monkeypatch.setenv("FEISHU_SECRET", "topsecret")
    body = notifier._build_body(NotificationPayload(text="hi"))
    assert "timestamp" in body and "sign" in body
    assert body["sign"] == sign("topsecret", int(body["timestamp"]))


def test_at_all_appended_to_text(notifier, monkeypatch):
    n = notifier
    n._at = {"all": True, "mobiles": []}
    body = n._build_body(NotificationPayload(text="broadcast"))
    assert "@all" in body["content"]["text"]


# ── response handling ───────────────────────────────────────────────────
def test_success_on_code_zero(notifier, monkeypatch):
    monkeypatch.setattr(
        feishu_mod.httpx, "post", lambda *a, **k: FakeResponse(200, {"code": 0, "msg": "success"})
    )
    res = notifier.send(NotificationPayload(text="x"))
    assert res.ok is True and res.status_code == 200


def test_failure_on_nonzero_code_not_retried(notifier, monkeypatch):
    calls = {"n": 0}

    def fake_post(*a, **k):
        calls["n"] += 1
        return FakeResponse(200, {"code": 19021, "msg": "rate limited"})

    monkeypatch.setattr(feishu_mod.httpx, "post", fake_post)
    res = notifier.send(NotificationPayload(text="x"))
    assert res.ok is False
    assert calls["n"] == 1  # HTTP 200 with error code is a client error → no retry


def test_server_error_is_retried(notifier, monkeypatch):
    calls = {"n": 0}

    def fake_post(*a, **k):
        calls["n"] += 1
        return FakeResponse(500, {"msg": "boom"}, raises_json=True)

    monkeypatch.setattr(feishu_mod.httpx, "post", fake_post)
    res = notifier.send(NotificationPayload(text="x"))
    assert res.ok is False
    assert calls["n"] == notifier.max_retries + 1


def test_network_exception_triggers_retry(notifier, monkeypatch):
    import httpx as _httpx

    calls = {"n": 0}

    def fake_post(*a, **k):
        calls["n"] += 1
        raise _httpx.ConnectError("down")

    monkeypatch.setattr(feishu_mod.httpx, "post", fake_post)
    res = notifier.send(NotificationPayload(text="x"))
    assert res.ok is False
    assert calls["n"] == notifier.max_retries + 1


# ── rate limiting ───────────────────────────────────────────────────────
def test_min_interval_blocks_second_send(notifier, monkeypatch):
    notifier.rate_limiter.min_interval = 1000  # force block after first
    monkeypatch.setattr(feishu_mod.httpx, "post", lambda *a, **k: FakeResponse(200, {"code": 0}))
    first = notifier.send(NotificationPayload(text="a"))
    second = notifier.send(NotificationPayload(text="b"))
    assert first.ok is True
    assert second.skipped is True and "rate limited" in second.error


def test_daily_cap_blocks(notifier, monkeypatch):
    notifier.rate_limiter.daily_cap = 1
    monkeypatch.setattr(feishu_mod.httpx, "post", lambda *a, **k: FakeResponse(200, {"code": 0}))
    assert notifier.send(NotificationPayload(text="a")).ok is True
    assert notifier.send(NotificationPayload(text="b")).skipped is True


# ── dry run ─────────────────────────────────────────────────────────────
def test_render_masks_sign(notifier, monkeypatch):
    monkeypatch.setenv("FEISHU_SECRET", "s3cr3t")
    rendered = notifier.render(NotificationPayload(text="x"))
    assert rendered["body"]["sign"] == "<signed>"
    assert rendered["url"].endswith("/hook/abc")


# ── config + registry ───────────────────────────────────────────────────
def test_get_notifiers_skips_unconfigured(monkeypatch, tmp_path):
    monkeypatch.delenv("FEISHU_WEBHOOK_URL", raising=False)
    cfg = load_notify_config(tmp_path / "missing.yml")
    assert get_notifiers(cfg) == []  # feishu enabled but env missing → skipped


def test_get_notifiers_includes_configured(monkeypatch, tmp_path):
    monkeypatch.setenv("FEISHU_WEBHOOK_URL", "https://open.feishu.cn/open-apis/bot/v2/hook/x")
    cfg = load_notify_config(tmp_path / "missing.yml")
    cfg["rate_limit"]["state_path"] = str(tmp_path / "s.json")
    notifiers = get_notifiers(cfg)
    assert [n.channel for n in notifiers] == ["feishu"]


def test_bare_hook_id_resolves_to_full_url(notifier):
    notifier._webhook_env = "FEISHU_WEBHOOK_URL"
    import os

    os.environ["FEISHU_WEBHOOK_URL"] = "just-a-hook-id"
    assert notifier._resolved_url() == feishu_mod._FEISHU_HOOK_BASE + "just-a-hook-id"


def test_default_payload_renders_json():
    payload = build_default_payload("https://radar.example")
    # Must be JSON-serializable (CLI dry-run relies on this).
    json.dumps(payload.card)
