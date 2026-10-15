"""Translation providers for the AI Radar i18n feature.

Only the *interface* is stable; concrete providers are pluggable and every one
degrades gracefully (returns no translation instead of raising) so a build with
no network / no key simply falls back to English.

Default provider (:class:`GoogleWebTranslator`) hits Google's free web
translate endpoint with ``httpx`` only — no extra dependency, no API key.
:class:`DeepLTranslator` is offered for higher quality when a key is present.
"""

from __future__ import annotations

import logging
import os
import random
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import cycle

import httpx

logger = logging.getLogger(__name__)

_GOOGLE_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
_GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
_DEEPL_ENDPOINTS = {
    "free": "https://api-free.deepl.com/v2/translate",
    "pro": "https://api.deepl.com/v2/translate",
}

# Target language code -> display name used in LLM translation prompts.
_TARGET_LANG_NAMES = {
    "zh-CN": "Simplified Chinese",
    "zh": "Simplified Chinese",
    "en": "English",
}


class Translator(ABC):
    """Minimal contract: translate many texts, return source -> target map."""

    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider can run in the current environment."""

    @abstractmethod
    def translate(self, texts: Iterable[str], target: str = "zh-CN") -> dict[str, str]:
        """Return a mapping of source text -> translated text.

        Implementations must never raise for network/rate reasons — omit any
        text they could not translate so the caller can retry it later.
        """


class GoogleWebTranslator(Translator):
    """Unofficial Google Translate web endpoint (free, keyless, rate-limited).

    Requests are issued concurrently — the endpoint is latency-bound, not
    throughput-bound, so a small worker pool cuts a full ~9k run from hours to
    minutes. Any text that errors or is rate-limited (non-200) is simply
    omitted, so the incremental cache retries it on the next run.
    """

    name = "google"

    def __init__(
        self,
        timeout: float = 10.0,
        max_workers: int = 6,
        retries: int = 3,
        backoff: float = 1.5,
    ) -> None:
        self._timeout = timeout
        self._workers = max(1, max_workers)
        self._retries = max(1, retries)
        self._backoff = backoff

    def is_available(self) -> bool:
        return True

    def translate(self, texts: Iterable[str], target: str = "zh-CN") -> dict[str, str]:
        items = [t for t in texts if t and t.strip()]
        if not items:
            return {}
        out: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=self._workers) as pool:
            futures = {pool.submit(self._translate_one, t, target): t for t in items}
            for fut in as_completed(futures):
                text = futures[fut]
                try:
                    translated = fut.result()
                except httpx.HTTPError as exc:
                    logger.debug("google translate failed for %r: %s", text[:40], exc)
                    continue
                if translated:
                    out[text] = translated
        return out

    def _translate_one(self, text: str, target: str) -> str | None:
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": target,
            "dt": "t",
            "q": text,
        }
        for attempt in range(self._retries):
            resp = httpx.get(_GOOGLE_ENDPOINT, params=params, timeout=self._timeout)
            if resp.status_code == 200:
                # Shape: [[[["译文", "原文", null, null, n]], ...], ...]
                data = resp.json()
                segments = data[0] if data and data[0] else []
                return "".join(seg[0] for seg in segments if seg and seg[0]) or None
            if resp.status_code == 429:
                # Rate-limited: back off (exponential + jitter) and retry. A
                # still-throttled text is skipped so it re-enters the pending
                # queue on the next incremental run.
                delay = self._backoff * (2**attempt) + random.uniform(0, 0.5)
                time.sleep(delay)
                continue
            return None  # other HTTP error: give up on this text for now
        return None


class DeepLTranslator(Translator):
    """DeepL API provider (higher quality, requires DEEPL_API_KEY)."""

    name = "deepl"

    def __init__(self, api_key: str | None = None, timeout: float = 15.0) -> None:
        self._key = api_key or os.environ.get("DEEPL_API_KEY", "").strip()
        self._timeout = timeout

    def is_available(self) -> bool:
        return bool(self._key)

    def translate(self, texts: Iterable[str], target: str = "zh-CN") -> dict[str, str]:
        items = [t for t in texts if t and t.strip()]
        if not items or not self._key:
            return {}
        endpoint = _DEEPL_ENDPOINTS["free" if self._key.endswith(":fx") else "pro"]
        out: dict[str, str] = {}
        # DeepL accepts multiple text[] params; batch in chunks to stay tidy.
        for i in range(0, len(items), 40):
            chunk = items[i : i + 40]
            try:
                resp = httpx.post(
                    endpoint,
                    headers={"Authorization": f"DeepL-Auth-Key {self._key}"},
                    data={"text": chunk, "target_lang": target.upper()},
                    timeout=self._timeout,
                )
                if resp.status_code == 200:
                    for src, res in zip(chunk, resp.json().get("translations", [])):
                        if res and res.get("text"):
                            out[src] = res["text"]
            except (httpx.HTTPError, ValueError) as exc:
                logger.debug("deepl translate failed: %s", exc)
                continue
        return out


class GroqTranslator(Translator):
    """LLM translation via Groq's OpenAI-compatible chat endpoint.

    Reuses the same credentials the classifier already uses (``GROQ_API_KEYS``,
    optionally rotated across several keys, and ``GROQ_MODEL``). Descriptions go
    out as numbered batches so one request covers many; any batch that errors or
    is rate-limited (429 -> ``raise_for_status``) is omitted so the incremental
    cache retries it next run. Groq's free tier is limited by request/token rate
    rather than a monthly character quota, and is fast — which makes it the most
    stable, cost-free choice for a Chinese-primary audience.
    """

    name = "groq"

    def __init__(
        self,
        api_keys: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
        batch_size: int = 25,
        min_interval: float = 0.3,
    ) -> None:
        keys_raw = api_keys if api_keys is not None else os.environ.get("GROQ_API_KEYS", "")
        self._keys = [k.strip() for k in keys_raw.split(",") if k.strip()]
        self._cycle = cycle(self._keys) if self._keys else None
        self._model = model or os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
        self._timeout = timeout
        self._batch_size = max(1, batch_size)
        self._min_interval = min_interval

    def is_available(self) -> bool:
        return bool(self._keys)

    def _next_key(self) -> str | None:
        return next(self._cycle) if self._cycle else None

    def translate(self, texts: Iterable[str], target: str = "zh-CN") -> dict[str, str]:
        items = [t for t in texts if t and t.strip()]
        if not items or not self._keys:
            return {}
        out: dict[str, str] = {}
        for i in range(0, len(items), self._batch_size):
            chunk = items[i : i + self._batch_size]
            try:
                out.update(self._translate_batch(chunk, target))
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                logger.debug("groq translate batch failed: %s", exc)
            time.sleep(self._min_interval)
        return out

    def _translate_batch(self, chunk: list[str], target: str) -> dict[str, str]:
        lang = _TARGET_LANG_NAMES.get(target, target)
        # One description per numbered line; collapse embedded newlines so the
        # line contract holds, while the cache stays keyed by the original text.
        lines = "\n".join(f"{idx}\t{' '.join(t.split())}" for idx, t in enumerate(chunk))
        payload = {
            "model": self._model,
            "temperature": 0.2,
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"You translate GitHub one-line project descriptions into {lang}. "
                        "Keep URLs, code spans, brand/product names and technical acronyms "
                        "(LLM, RAG, MCP, API ...) unchanged. Output ONLY lines of the exact "
                        "form 'N<TAB>translation', one per input line, same order and "
                        "numbering. No explanations, no headers, no markdown fences."
                    ),
                },
                {"role": "user", "content": lines},
            ],
        }
        resp = httpx.post(
            _GROQ_ENDPOINT,
            headers={
                "Authorization": f"Bearer {self._next_key()}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return self._parse(content, chunk)

    @staticmethod
    def _parse(content: str, chunk: list[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for raw in content.splitlines():
            line = raw.strip()
            if not line:
                continue
            if "\t" in line:
                head, _, body = line.partition("\t")
            else:
                # Tolerate 'N: text' / 'N. text' the model may emit anyway.
                m = re.match(r"^(\d+)\s*[:.\-)]\s*(.*)$", line)
                if not m:
                    continue
                head, body = m.group(1), m.group(2)
            try:
                idx = int(head.strip())
            except ValueError:
                continue
            body = body.strip()
            if 0 <= idx < len(chunk) and body:
                out[chunk[idx]] = body
        return out


def get_provider(name: str = "auto") -> Translator:
    """Resolve a provider by name with a stability-first fallback chain.

    ``auto`` prefers Groq (already used for classification: free, fast, quota by
    rate not characters, strong at Chinese + tech terms), then DeepL when a key
    is present, then the keyless Google web endpoint. Explicit selections fall
    through the same chain when their key is missing, so a build never hard-
    fails — it simply uses whatever is configured.
    """
    if name in ("groq", "auto"):
        groq = GroqTranslator()
        if groq.is_available():
            return groq
        if name == "groq":
            logger.warning("groq requested but GROQ_API_KEYS missing; using fallback")
    if name in ("deepl", "auto"):
        deepl = DeepLTranslator()
        if deepl.is_available():
            return deepl
        if name == "deepl":
            logger.warning("deepl requested but DEEPL_API_KEY missing; using google")
    return GoogleWebTranslator()
