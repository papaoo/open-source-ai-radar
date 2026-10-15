"""Feishu (Lark) group custom-bot notifier.

Delivery target is a *custom bot webhook* created inside a Feishu group:
    https://open.feishu.cn/open-apis/bot/v2/hook/<HOOK_ID>

Security uses the bot's optional signing secret. The signature algorithm mirrors
the one documented on the Feishu Open Platform (and implemented across official
SDKs such as ``lark-oapi``):

    string_to_sign = f"{timestamp}\\n{secret}"
    hmac_code      = HMAC-SHA256(key=string_to_sign, msg=b"")
    sign           = base64(hmac_code)

and is sent alongside ``timestamp`` in the JSON body. This module reproduces
that documented scheme; it does not vendor third-party code, keeping the runtime
dependency surface to ``httpx`` only.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import logging
import os
import time
from typing import Any

import httpx

from radar.notifications.base import NotificationPayload, Notifier, NotifyResult
from radar.notifications.card import build_text_card

logger = logging.getLogger(__name__)

# Official domains for the custom-bot webhook. The URL itself normally comes
# straight from the environment; these are only used when a bare hook id is
# supplied instead of a full URL.
_FEISHU_HOOK_BASE = "https://open.feishu.cn/open-apis/bot/v2/hook/"
_LARK_HOOK_BASE = "https://open.larksuite.com/open-apis/bot/v2/hook/"


def sign(secret: str, timestamp: int) -> str:
    """Return the Feishu bot signature for ``timestamp`` + ``secret``.

    Implements the documented HMAC-SHA256(key=f"{timestamp}\\n{secret}", msg="")
    encoded as base64.
    """
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


class FeishuBotNotifier(Notifier):
    """Send messages to a Feishu/Lark group via a custom-bot webhook."""

    channel = "feishu"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        ch = (self.config.get("channels", {}) or {}).get("feishu", {}) or {}
        self._webhook_env = ch.get("webhook_url_env", "FEISHU_WEBHOOK_URL")
        self._secret_env = ch.get("secret_env", "FEISHU_SECRET")
        self._domain = ch.get("domain", "feishu")
        card_cfg = ch.get("card", {}) or {}
        self._theme = card_cfg.get("theme", "blue")
        self._action_label = card_cfg.get("action_label", "View Radar")
        self._at = ch.get("at", {}) or {}

    # -- configuration ---------------------------------------------------
    @property
    def webhook_url(self) -> str:
        return os.environ.get(self._webhook_env, "").strip()

    @property
    def secret(self) -> str:
        return os.environ.get(self._secret_env, "").strip()

    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    def _resolved_url(self) -> str:
        url = self.webhook_url
        if url.startswith("http://") or url.startswith("https://"):
            return url
        # Allow passing a bare hook id.
        base = _LARK_HOOK_BASE if self._domain == "lark" else _FEISHU_HOOK_BASE
        return base + url

    # -- payload building ------------------------------------------------
    def _build_body(self, payload: NotificationPayload) -> dict[str, Any]:
        body: dict[str, Any] = {}

        ctype = payload.content_type()
        if ctype == "card":
            card = payload.card or build_text_card(
                payload.text or payload.title or "", theme=self._theme
            )
            body["msg_type"] = "interactive"
            body["card"] = card
        elif ctype == "post":
            body["msg_type"] = "post"
            body["content"] = {"post": payload.post or {}}
        else:  # text
            text = payload.text or ""
            # Append @all / @mobile mentions to the plain-text body.
            text = self._apply_at(text)
            body["msg_type"] = "text"
            body["content"] = {"text": text}

        if self.secret:
            ts = int(time.time())
            body["timestamp"] = str(ts)
            body["sign"] = sign(self.secret, ts)

        return body

    def _apply_at(self, text: str) -> str:
        at_parts: list[str] = []
        if self._at.get("all"):
            at_parts.append("@all")
        for mobile in self._at.get("mobiles", []) or []:
            at_parts.append(f"@{mobile}")
        if not at_parts:
            return text
        mention_line = " ".join(at_parts)
        return f"{text}\n{mention_line}" if text else mention_line

    # -- sending ---------------------------------------------------------
    def _send_once(self, payload: NotificationPayload) -> NotifyResult:
        body = self._build_body(payload)
        try:
            resp = httpx.post(self._resolved_url(), json=body, timeout=self.timeout)
        except httpx.HTTPError:
            # Network/timeout errors are transient → re-raise so base retries.
            raise

        status = resp.status_code
        data: dict[str, Any] = {}
        with contextlib.suppress(ValueError):
            data = resp.json()

        # Feishu returns HTTP 200 with code==0 on success; failure codes may be
        # non-zero (e.g. 9499 wrong sign, 19021 rate limited).
        code = data.get("code", data.get("StatusCode", 0))
        msg = data.get("msg") or data.get("StatusMessage") or ""

        if status == 200 and code == 0:
            return NotifyResult(ok=True, channel=self.channel, status_code=status, payload=body)

        error = f"feishu code={code} msg={msg!r}" if code else f"HTTP {status}: {msg!r}"
        return NotifyResult(
            ok=False, channel=self.channel, status_code=status, error=error, payload=body
        )

    def render(self, payload: NotificationPayload) -> dict[str, Any]:
        """Dry-run render (mask the sign for safety in logs)."""
        body = self._build_body(payload)
        if "sign" in body:
            body = {**body, "sign": "<signed>"}
        return {"channel": self.channel, "url": self._resolved_url(), "body": body}


def build_default_payload(site_url: str | None = None) -> NotificationPayload:
    """Placeholder payload so callers can wire the module before deciding content.

    Replace this with real digest/report content in a later milestone; nothing in
    the delivery module needs to change to do so.
    """
    title = "Open Source AI Radar — 连通性测试"
    body = "**推送模块已就绪** ✅\n这是来自 AI Radar 通知模块的测试消息。"
    card = build_text_card(body, title=title, theme="blue")
    return NotificationPayload(
        text=body,
        card=card,
        title=title,
        link=site_url or None,
    )
