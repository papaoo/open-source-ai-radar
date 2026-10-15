"""Feishu interactive-card JSON builders.

The card structure follows the Feishu/Lark Open Platform message-card schema
(see https://open.feishu.cn/document for ``msg_type: interactive`` cards). Only
the *skeleton* is produced here — header, markdown div blocks, dividers and
action buttons — so business content stays decoupled from delivery. Callers pass
in the markdown they want rendered.

Card JSON layout reference (2.0-style element list understood by custom bots):
    {
      "config": {"wide_title_mode": false, "enable_forward": true},
      "header": {"title": {"tag": "plain_text", "content": ...},
                 "template": "<color>"},
      "elements": [ {"tag": "div"|"hr"|"action", ...}, ... ]
    }
"""

from __future__ import annotations

from typing import Any

# Header color templates accepted by Feishu card renderer.
VALID_THEMES = {
    "blue",
    "green",
    "grey",
    "violet",
    "yellow",
    "red",
    "turquoise",
    "wathet",
    "carmine",
    "golden",
    "orange",
    "pink",
    "purple",
}

DEFAULT_THEME = "blue"


def _md_div(content: str) -> dict[str, Any]:
    return {"tag": "div", "text": {"tag": "lark_md", "content": content}}


def _hr() -> dict[str, Any]:
    return {"tag": "hr"}


def _button(text: str, url: str, *, primary: bool = True) -> dict[str, Any]:
    btn: dict[str, Any] = {
        "tag": "button",
        "text": {"tag": "plain_text", "content": text},
        "url": url,
        "width": "auto",
    }
    if primary:
        btn["type"] = "primary"
    return btn


def build_card(
    title: str,
    markdown_blocks: list[str] | str,
    *,
    link: str | None = None,
    action_label: str = "View Radar",
    theme: str = DEFAULT_THEME,
    extra_elements: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Assemble a minimal-but-valid Feishu interactive card.

    Args:
        title: card header text.
        markdown_blocks: one or more ``lark_md`` strings rendered as div blocks.
        link: optional URL for the primary action button.
        action_label: label for the action button.
        theme: header color template (see :data:`VALID_THEMES`).
        extra_elements: raw card elements appended after the markdown blocks
            (advanced use; validated lightly, not deeply).
    """
    if isinstance(markdown_blocks, str):
        markdown_blocks = [markdown_blocks]

    if theme not in VALID_THEMES:
        theme = DEFAULT_THEME

    elements: list[dict[str, Any]] = []
    for i, block in enumerate(markdown_blocks):
        if not block:
            continue
        elements.append(_md_div(block))
        # Divider between successive content blocks (not after the last).
        if i < len(markdown_blocks) - 1:
            elements.append(_hr())

    if extra_elements:
        elements.extend(extra_elements)

    if link:
        elements.append({"tag": "action", "actions": [_button(action_label, link)]})

    card: dict[str, Any] = {
        "config": {"wide_title_mode": False, "enable_forward": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": theme,
        },
        "elements": elements,
    }
    return card


def build_text_card(
    body: str, *, title: str = "Open Source AI Radar", theme: str = DEFAULT_THEME
) -> dict[str, Any]:
    """Convenience: a single-block card from one markdown string."""
    return build_card(title, [body], theme=theme)
