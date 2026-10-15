"""Notification subsystem for Open Source AI Radar.

Public API:
    - :func:`load_notify_config` — read ``config/notify.yml`` with defaults.
    - :func:`get_notifiers` — instantiate enabled channels from config + env.
    - :class:`FeishuBotNotifier` — the Feishu group custom-bot channel.
    - :class:`NotificationPayload` / :class:`NotifyResult` — delivery contracts.

The subsystem is content-agnostic: build a payload, hand it to a notifier.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from radar.notifications.base import (
    NotificationPayload,
    Notifier,
    NotifyResult,
    RateLimiter,
)
from radar.notifications.card import build_card, build_text_card
from radar.notifications.feishu import FeishuBotNotifier, build_default_payload, sign

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "notify.yml"

_DEFAULTS: dict[str, Any] = {
    "site_url": "",
    "channels": {
        "feishu": {
            "enabled": True,
            "webhook_url_env": "FEISHU_WEBHOOK_URL",
            "secret_env": "FEISHU_SECRET",
            "domain": "feishu",
            "card": {"theme": "blue", "action_label": "View Radar"},
            "at": {"all": False, "mobiles": []},
        },
    },
    "rate_limit": {
        "min_interval_seconds": 3,
        "daily_cap": 100,
        "state_path": "data/.notify_state.json",
    },
}

# Registry of channel name -> notifier class. Add new channels here.
_CHANNEL_REGISTRY: dict[str, type[Notifier]] = {
    "feishu": FeishuBotNotifier,
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_notify_config(path: Path | None = None) -> dict[str, Any]:
    """Load ``config/notify.yml`` merged over built-in defaults."""
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        logger.info("notify config not found at %s, using defaults", config_path)
        return _deep_merge(_DEFAULTS, {})
    try:
        with open(config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        if not isinstance(raw, dict):
            logger.warning("notify config is not a mapping, using defaults")
            return _deep_merge(_DEFAULTS, {})
        return _deep_merge(_DEFAULTS, raw)
    except Exception as exc:  # config load must never crash callers
        logger.error("failed to load notify config: %s", exc)
        return _deep_merge(_DEFAULTS, {})


def get_notifiers(
    config: dict[str, Any] | None = None,
    *,
    require_configured: bool = True,
) -> list[Notifier]:
    """Return instantiated notifiers for every enabled channel.

    A channel is considered enabled when its config ``enabled`` is true and the
    concrete notifier reports :meth:`is_configured` (i.e. required env vars are
    present). Channels that are enabled but unconfigured are skipped silently so
    CI runs without secrets do not fail. When ``require_configured`` is False,
    unconfigured channels are still returned (used by ``--dry-run`` so payloads
    can be previewed without credentials).
    """
    cfg = config or load_notify_config()
    channels = cfg.get("channels", {}) or {}

    notifiers: list[Notifier] = []
    for name, cls in _CHANNEL_REGISTRY.items():
        ch_cfg = channels.get(name, {})
        if isinstance(ch_cfg, dict) and not ch_cfg.get("enabled", True):
            continue
        # Pass the whole config so the notifier can read its slice + rate limit.
        notifier = cls(cfg)
        if notifier.is_configured():
            notifiers.append(notifier)
        elif require_configured:
            logger.info("channel %r enabled but not configured (missing env); skipped", name)
        else:
            notifiers.append(notifier)
    return notifiers


__all__ = [
    "FeishuBotNotifier",
    "NotificationPayload",
    "Notifier",
    "NotifyResult",
    "RateLimiter",
    "build_card",
    "build_default_payload",
    "build_text_card",
    "get_notifiers",
    "load_notify_config",
    "sign",
]
