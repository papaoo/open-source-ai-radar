"""Notification channel abstractions for Open Source AI Radar.

This package is deliberately **content-agnostic**: it defines *how* a message
is delivered, not *what* is sent. Concrete callers (weekly report, daily
digest, ...) build a :class:`NotificationPayload` and hand it to a
:class:`Notifier`. Today only a Feishu group custom-bot channel exists, but the
interface is designed so additional channels can be registered without touching
callers.
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NotificationPayload:
    """Channel-agnostic notification payload.

    Exactly one of ``text`` / ``post`` / ``card`` should be populated:

    - ``text``: plain-text body.
    - ``post``: rich-text ("post") body dict, channel-interpreted.
    - ``card``: interactive card JSON (see :mod:`radar.notifications.card`).

    ``title`` and ``link`` are optional hints used by channels that support a
    heading or an action button (e.g. the Feishu card header / button).
    """

    text: str | None = None
    post: dict[str, Any] | None = None
    card: dict[str, Any] | None = None
    title: str | None = None
    link: str | None = None

    def content_type(self) -> str:
        if self.card is not None:
            return "card"
        if self.post is not None:
            return "post"
        return "text"


@dataclass
class NotifyResult:
    """Outcome of a single :meth:`Notifier.send` call."""

    ok: bool
    channel: str
    status_code: int | None = None
    error: str | None = None
    skipped: bool = False
    payload: dict[str, Any] | None = None

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        if self.skipped:
            return f"[{self.channel}] skipped: {self.error or 'not configured'}"
        if self.ok:
            return f"[{self.channel}] ok (HTTP {self.status_code})"
        return f"[{self.channel}] failed (HTTP {self.status_code}): {self.error}"


class RateLimiter:
    """File-backed throttle shared across notifier instances.

    Enforces a minimum interval between sends and a per-day cap. State persists
    to a small JSON file so batch/CI runs across invocations stay bounded.
    """

    def __init__(
        self,
        state_path: str | Path = "data/.notify_state.json",
        min_interval_seconds: float = 0.0,
        daily_cap: int = 0,
        channel: str = "base",
    ) -> None:
        self.state_path = Path(state_path)
        self.min_interval = max(0.0, float(min_interval_seconds))
        self.daily_cap = max(0, int(daily_cap))
        self.channel = channel

    def _load(self) -> dict[str, Any]:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _save(self, state: dict[str, Any]) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except OSError as exc:  # pragma: no cover - best-effort persistence
            logger.warning("Could not persist notify rate-limit state: %s", exc)

    def check(self) -> tuple[bool, str | None]:
        """Return ``(allowed, reason)``. Does not sleep — callers decide."""
        state = self._load()
        ch = state.get(self.channel, {})
        today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        count = ch.get("count", 0) if ch.get("date") == today else 0
        if self.daily_cap and count >= self.daily_cap:
            return False, f"daily cap ({self.daily_cap}) reached"
        last = ch.get("last_ts", 0)
        if self.min_interval and (time.time() - last) < self.min_interval:
            return False, "min interval not elapsed"
        return True, None

    def record(self) -> None:
        """Record a successful send for throttle bookkeeping."""
        state = self._load()
        ch = state.get(self.channel, {})
        today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        count = ch.get("count", 0) if ch.get("date") == today else 0
        state[self.channel] = {"date": today, "count": count + 1, "last_ts": time.time()}
        self._save(state)


class Notifier(ABC):
    """Base class every notification channel implements."""

    channel: str = "base"
    timeout: float = 10.0
    max_retries: int = 2
    backoff_base: float = 0.5

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = config or {}
        rl = self.config.get("rate_limit", {})
        self.rate_limiter = RateLimiter(
            state_path=rl.get("state_path", "data/.notify_state.json"),
            min_interval_seconds=rl.get("min_interval_seconds", 0),
            daily_cap=rl.get("daily_cap", 0),
            channel=self.channel,
        )

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True when required env/config are present to actually send."""

    @abstractmethod
    def _send_once(self, payload: NotificationPayload) -> NotifyResult:
        """Perform a single delivery attempt (no retry logic here)."""

    def send(self, payload: NotificationPayload) -> NotifyResult:
        """Send ``payload`` with retry + rate-limit handling.

        Transient failures (raised exceptions or HTTP 5xx) are retried with
        exponential backoff. Permanent failures and skips return immediately.
        """
        if not self.is_configured():
            logger.info("[%s] not configured, skipping send", self.channel)
            return NotifyResult(
                ok=False, channel=self.channel, skipped=True, error="not configured"
            )

        allowed, reason = self.rate_limiter.check()
        if not allowed:
            logger.warning("[%s] rate limited: %s", self.channel, reason)
            return NotifyResult(
                ok=False, channel=self.channel, skipped=True, error=f"rate limited: {reason}"
            )

        result = self._attempt_with_retry(payload)
        if result.ok:
            self.rate_limiter.record()
        return result

    def _attempt_with_retry(self, payload: NotificationPayload) -> NotifyResult:
        last: NotifyResult | None = None
        for attempt in range(self.max_retries + 1):
            try:
                res = self._send_once(payload)
            except Exception as exc:  # isolate channel errors, retry in base
                logger.warning("[%s] attempt %d raised: %s", self.channel, attempt + 1, exc)
                last = NotifyResult(ok=False, channel=self.channel, error=str(exc))
            else:
                last = res

            if last.ok:
                return last

            # Non-5xx client errors are not retryable.
            if last.status_code is not None and last.status_code < 500:
                return last

            if attempt < self.max_retries:
                delay = self.backoff_base * (2**attempt)
                logger.info("[%s] retrying in %.1fs", self.channel, delay)
                time.sleep(delay)

        return last or NotifyResult(ok=False, channel=self.channel, error="unknown error")

    def render(self, payload: NotificationPayload) -> dict[str, Any]:
        """Return the wire payload dict without sending (for ``--dry-run``).

        Channels override this; the default wraps the content type generically.
        """
        return {"channel": self.channel, "content_type": payload.content_type()}
