"""Gemini via OpenAI-compatible API — preserve thought signatures on tool calls.

Gemini 3+ rejects multi-turn tool use when ``extra_content.google.thought_signature``
is dropped between turns. Stock ``ChatOpenAI`` only serializes OpenAI-spec tool_call
fields and strips provider extras.
"""

from __future__ import annotations

from typing import Any, Literal

import openai
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from langchain_openai.chat_models.base import (
    ChatOpenAI,
    _convert_dict_to_message,
    _convert_from_v1_to_chat_completions,
    _convert_message_to_dict,
)

# Matches upstream langchain-openai fix for Gemini multi-turn tools.
OPENAI_TOOL_CALL_EXTRAS_KEY = "__openai_tool_call_extras__"

_OPENAI_TOOL_CALL_SPEC_KEYS = frozenset({"id", "type", "function"})


def _tool_call_extras(raw_tool_call: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in raw_tool_call.items() if k not in _OPENAI_TOOL_CALL_SPEC_KEYS}


def _thought_signature_from_tool_call(raw: dict[str, Any]) -> str | None:
    extra = raw.get("extra_content") if isinstance(raw.get("extra_content"), dict) else {}
    google = extra.get("google") if isinstance(extra.get("google"), dict) else {}
    sig = google.get("thought_signature")
    if sig:
        return str(sig)
    root = raw.get("thought_signature")
    return str(root) if root else None


def propagate_thought_signatures(raw_tool_calls: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Gemini 3 often attaches one signature per assistant turn; all parallel calls need it."""
    if not raw_tool_calls:
        return []
    updated = [dict(tc) for tc in raw_tool_calls]
    signature: str | None = None
    for tc in updated:
        signature = _thought_signature_from_tool_call(tc) or signature
    if not signature:
        return updated
    for tc in updated:
        if _thought_signature_from_tool_call(tc):
            continue
        extra = tc.setdefault("extra_content", {})
        google = extra.setdefault("google", {})
        google["thought_signature"] = signature
    return updated


def _thought_signature_from_assistant_dict(message_dict: dict[str, Any]) -> str | None:
    for tc in message_dict.get("tool_calls") or []:
        if isinstance(tc, dict):
            sig = _thought_signature_from_tool_call(tc)
            if sig:
                return sig
    content = message_dict.get("content")
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            sig = part.get("thought_signature")
            if sig:
                return str(sig)
            google = part.get("google")
            if isinstance(google, dict) and google.get("thought_signature"):
                return str(google["thought_signature"])
    root = message_dict.get("thought_signature")
    return str(root) if root else None


def _merge_stored_tool_calls(
    serialized: list[dict[str, Any]],
    stored: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {str(tc.get("id")): tc for tc in stored if tc.get("id")}
    merged: list[dict[str, Any]] = []
    for idx, tool_call in enumerate(serialized):
        call_id = tool_call.get("id")
        stored_row = by_id.get(str(call_id)) if call_id else None
        if stored_row is None and idx < len(stored):
            stored_row = stored[idx]
        if stored_row:
            merged.append({**tool_call, **_tool_call_extras(stored_row)})
        else:
            merged.append(tool_call)
    return propagate_thought_signatures(merged)


def capture_tool_call_extras(raw_tool_calls: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    captured: dict[str, dict[str, Any]] = {}
    for raw in raw_tool_calls or []:
        call_id = raw.get("id")
        if not call_id:
            continue
        extra = _tool_call_extras(raw)
        if extra:
            captured[str(call_id)] = extra
    return captured


def attach_tool_call_extras(message: AIMessage, raw_tool_calls: list[dict[str, Any]] | None) -> None:
    normalized = propagate_thought_signatures(list(raw_tool_calls or []))
    captured = capture_tool_call_extras(normalized)
    if not captured and not normalized:
        return
    if captured:
        message.additional_kwargs[OPENAI_TOOL_CALL_EXTRAS_KEY] = captured
    # Full raw tool_calls for replay when LangChain rebuilds from additional_kwargs.
    message.additional_kwargs["tool_calls"] = normalized


def gemini_convert_message_to_dict(
    message: BaseMessage,
    api: Literal["chat/completions", "responses"] = "chat/completions",
) -> dict[str, Any]:
    message_dict = _convert_message_to_dict(message, api=api)
    if not isinstance(message, AIMessage) or not message_dict.get("tool_calls"):
        return message_dict

    stored = message.additional_kwargs.get("tool_calls")
    if isinstance(stored, list) and stored:
        message_dict["tool_calls"] = _merge_stored_tool_calls(message_dict["tool_calls"], stored)
    else:
        extras_by_id = message.additional_kwargs.get(OPENAI_TOOL_CALL_EXTRAS_KEY) or {}
        if extras_by_id:
            merged: list[dict[str, Any]] = []
            for tool_call in message_dict["tool_calls"]:
                call_id = tool_call.get("id")
                extra = extras_by_id.get(call_id) if call_id else None
                merged.append({**tool_call, **(extra or {})})
            message_dict["tool_calls"] = merged
    message_dict["tool_calls"] = propagate_thought_signatures(message_dict["tool_calls"])
    return message_dict


def _response_to_dict(response: dict[str, Any] | openai.BaseModel) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    return response.model_dump(
        exclude={"choices": {"__all__": {"message": {"parsed"}}}},
        warnings=False,
    )


class GeminiChatOpenAI(ChatOpenAI):
    """ChatOpenAI pointed at Gemini with thought-signature-safe tool call round-trips."""

    def _get_request_payload(
        self,
        input_: Any,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        messages = self._convert_input(input_).to_messages()
        if stop is not None:
            kwargs["stop"] = stop

        payload = {**self._default_params, **kwargs}
        if self._use_responses_api(payload):
            return super()._get_request_payload(input_, stop=stop, **kwargs)

        serialized: list[dict[str, Any]] = []
        for message in messages:
            if isinstance(message, AIMessage):
                message = _convert_from_v1_to_chat_completions(message)
            serialized.append(gemini_convert_message_to_dict(message))
        payload["messages"] = serialized
        return payload

    def _create_chat_result(
        self,
        response: dict | openai.BaseModel,
        generation_info: dict | None = None,
    ) -> ChatResult:
        result = super()._create_chat_result(response, generation_info=generation_info)
        try:
            response_dict = _response_to_dict(response)
            choices = response_dict.get("choices") or []
        except Exception:
            return result

        for generation, choice in zip(result.generations, choices, strict=False):
            raw_message = choice.get("message") if isinstance(choice, dict) else None
            if not raw_message:
                continue
            raw_tool_calls = list(raw_message.get("tool_calls") or [])
            signature = _thought_signature_from_assistant_dict(raw_message)
            if signature and raw_tool_calls:
                for tc in raw_tool_calls:
                    if not isinstance(tc, dict):
                        continue
                    if _thought_signature_from_tool_call(tc):
                        continue
                    extra = tc.setdefault("extra_content", {})
                    google = extra.setdefault("google", {})
                    google.setdefault("thought_signature", signature)
            raw_tool_calls = propagate_thought_signatures(raw_tool_calls)
            if not raw_tool_calls:
                continue
            message = generation.message
            if isinstance(message, AIMessage):
                attach_tool_call_extras(message, raw_tool_calls)
        return result


def gemini_dict_to_message(message_dict: dict[str, Any]) -> BaseMessage:
    """Parse an OpenAI-style assistant message and stash Gemini tool-call extras."""
    message = _convert_dict_to_message(message_dict)
    if isinstance(message, AIMessage):
        attach_tool_call_extras(message, message_dict.get("tool_calls"))
    return message
