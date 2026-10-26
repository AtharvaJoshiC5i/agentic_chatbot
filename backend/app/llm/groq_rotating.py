"""Groq chat model with multiple API keys, per-key RPM limits, and 429 failover."""

from __future__ import annotations

import threading
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from pydantic import ConfigDict, Field, PrivateAttr

from app.config import get_settings
from app.llm.rate_limit import acquire_llm_slot

GROQ_DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
from app.llm.retry import invoke_with_backoff, is_rate_limit_error


class _KeyRoundRobin:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cursor = 0

    def next_start(self, count: int) -> int:
        if count <= 0:
            return 0
        with self._lock:
            start = self._cursor % count
            self._cursor += 1
            return start


_round_robin = _KeyRoundRobin()


class GroqRotatingChatModel(BaseChatModel):
    """LangChain chat model that spreads load across multiple Groq API keys."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model_name: str = Field(alias="model")
    base_url: str = GROQ_DEFAULT_BASE_URL
    temperature: float = 0.0
    max_rpm_per_key: int = 30

    _tools_args: tuple[Any, ...] | None = PrivateAttr(default=None)
    _tools_kwargs: dict[str, Any] | None = PrivateAttr(default=None)

    @property
    def _llm_type(self) -> str:
        return "groq-rotating"

    def _api_keys(self) -> list[str]:
        keys = get_settings().groq_api_keys_list
        if not keys:
            raise RuntimeError("GROQ_API_KEY / GROQ_API_KEYS is not configured.")
        return keys

    def _chat_for_key(self, api_key: str) -> Any:
        llm: Any = ChatOpenAI(
            model=self.model_name,
            api_key=api_key,
            base_url=self.base_url or GROQ_DEFAULT_BASE_URL,
            temperature=self.temperature,
        )
        if self._tools_args is not None:
            kwargs = self._tools_kwargs or {}
            llm = llm.bind_tools(*self._tools_args, **kwargs)
        return llm

    def _ordered_key_indices(self) -> list[tuple[int, str]]:
        keys = self._api_keys()
        start = _round_robin.next_start(len(keys))
        order: list[tuple[int, str]] = []
        for offset in range(len(keys)):
            idx = (start + offset) % len(keys)
            order.append((idx, keys[idx]))
        return order

    def _run_on_key(
        self,
        key_index: int,
        api_key: str,
        messages: list[BaseMessage],
        stop: list[str] | None,
        run_manager: Any,
        config: RunnableConfig | None,
        kwargs: dict[str, Any],
    ) -> ChatResult:
        acquire_llm_slot(f"groq:{key_index}", self.max_rpm_per_key)
        chat = self._chat_for_key(api_key)
        if isinstance(chat, BaseChatModel):
            return chat._generate(
                messages,
                stop=stop,
                run_manager=run_manager,
                config=config,
                **kwargs,
            )
        ai_message = chat.invoke(messages, stop=stop, config=config, **kwargs)
        if not isinstance(ai_message, AIMessage):
            ai_message = AIMessage(content=str(ai_message))
        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        config: RunnableConfig | None = kwargs.pop("config", None)
        ordered = self._ordered_key_indices()
        last_rate_exc: BaseException | None = None

        for attempt, (key_index, api_key) in enumerate(ordered):

            def call(
                _key_index: int = key_index,
                _api_key: str = api_key,
            ) -> ChatResult:
                return self._run_on_key(
                    _key_index,
                    _api_key,
                    messages,
                    stop,
                    run_manager,
                    config,
                    kwargs,
                )

            try:
                return invoke_with_backoff(call, max_attempts=2)
            except BaseException as exc:  # noqa: BLE001
                if is_rate_limit_error(exc) and attempt < len(ordered) - 1:
                    last_rate_exc = exc
                    continue
                raise

        assert last_rate_exc is not None
        raise last_rate_exc

    def invoke(
        self,
        input: list[BaseMessage],
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AIMessage:
        result = self._generate(input, config=config, **kwargs)
        return result.generations[0].message

    def _wrap_tools(self, *args: Any, **kwargs: Any) -> GroqRotatingChatModel:
        clone = GroqRotatingChatModel(
            model=self.model_name,
            base_url=self.base_url,
            temperature=self.temperature,
            max_rpm_per_key=self.max_rpm_per_key,
        )
        clone._tools_args = args
        clone._tools_kwargs = kwargs
        return clone

    def bind_tools(self, *args: Any, **kwargs: Any) -> GroqRotatingChatModel:
        return self._wrap_tools(*args, **kwargs)

    def with_config(self, config: RunnableConfig | None = None, **kwargs: Any) -> GroqRotatingChatModel:
        bound = super().with_config(config, **kwargs)
        if isinstance(bound, GroqRotatingChatModel):
            bound._tools_args = self._tools_args
            bound._tools_kwargs = self._tools_kwargs
        return bound
