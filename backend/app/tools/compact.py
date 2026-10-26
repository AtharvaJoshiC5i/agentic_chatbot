"""Shrink tool payloads before they are fed back to the LLM."""

import json
from typing import Any

from app.agents.limits import MAX_TOOL_JSON_CHARS


def compact_json(data: Any, *, max_chars: int = MAX_TOOL_JSON_CHARS) -> str:
    text = json.dumps(data, default=str)
    if len(text) <= max_chars:
        return text
    return json.dumps(
        {
            "truncated": True,
            "original_length": len(text),
            "preview": text[: max_chars - 120],
            "hint": "Use narrower tool arguments or a specific return_id.",
        },
        default=str,
    )
