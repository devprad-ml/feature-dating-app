"""
Thin Claude client. Two callable functions, both return parsed dicts.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from anthropic import Anthropic

from . import prompts
from .config import settings

logger = logging.getLogger(__name__)

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add a key."
            )
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip().rstrip("`").strip()
    return json.loads(text)


def _call(system: str, user: str, *, max_tokens: int = 800) -> Any:
    client = _get_client()
    msg = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    raw = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    try:
        return _extract_json(raw)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned non-JSON: %r", raw[:500])
        raise ValueError(f"LLM returned invalid JSON: {exc}") from exc


# ---------- public API ----------

def analyze_memory(memory_text: str) -> dict[str, Any]:
    data = _call(prompts.SYSTEM_MEMORY_ANALYZE, prompts.build_analyze_user_message(memory_text))
    required = {"themes", "emotional_register", "lesson", "one_line_essence"}
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"Memory analysis missing fields: {missing}")
    if not isinstance(data["themes"], list) or not data["themes"]:
        raise ValueError("Memory analysis returned empty themes")
    return data


def resonance_reason(viewer: dict[str, Any], candidate: dict[str, Any]) -> str:
    """Return a one-line resonance sentence between two analyzed memories.

    Falls back to a templated sentence if the LLM call fails — the demo still
    works without a key, just less interesting.
    """
    try:
        data = _call(
            prompts.SYSTEM_RESONANCE_REASON,
            prompts.build_resonance_user_message(viewer, candidate),
            max_tokens=200,
        )
        sentence = str(data.get("reason", "")).strip()
        if sentence:
            return sentence
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM resonance reason failed (%s); using fallback", exc)

    overlap = sorted(set(viewer["themes"]) & set(candidate["themes"]))
    if overlap:
        return f"You both write about {', '.join(overlap)}."
    return "Different shapes of memory, same kind of attention."
