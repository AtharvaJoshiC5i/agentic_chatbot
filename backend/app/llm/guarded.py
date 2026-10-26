"""LangChain chat model wrapper: RPM gate + 429 backoff."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableConfig
from pydantic import ConfigDict, Field

from app.llm.context_window import fit_messages_to_context_budget
from app.llm.rate_limit import acquire_llm_slot
from app.llm.retry import invoke_with_backoff

try:
    from app.llm.gemini_openai_compat import GeminiChatOpenAI
except ImportError:  # pragma: no cover
    GeminiChatOpenAI = None  # type: ignore[misc, assignment]


class GuardedChatModel(BaseChatModel):
    """Wraps any chat model with per-provider rate limiting and retry.

    ``inner`` may be a ``BaseChatModel`` or a Runnable binding returned by
    ``bind_tools`` / ``with_config`` (not a ``BaseChatModel`` subclass).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    inner: Any = Field(description="Chat model or LangChain binding")
    provider_id: str
    max_rpm: int

    @property
    def _llm_type(self) -> str:
        return f"guarded-{self.provider_id}"

    def _wrap(self, inner: Any) -> GuardedChatModel:
        return GuardedChatModel.model_construct(
            inner=inner,
            provider_id=self.provider_id,
            max_rpm=self.max_rpm,
        )

    def _unwrap_gemini_chat_model(self) -> Any | None:
        """Find GeminiChatOpenAI under tool bindings so _get_request_payload runs."""
        if GeminiChatOpenAI is None:
            return None
        seen: set[int] = set()
        current: Any = self.inner
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if isinstance(current, GeminiChatOpenAI):
                return current
            if isinstance(current, GuardedChatModel):
                current = current.inner
                continue
            bound = getattr(current, "bound", None)
            if bound is not None:
                current = bound
                continue
            break
        return None

    def _prepare_messages(
        self,
        messages: list[BaseMessage],
        config: RunnableConfig | None,
    ) -> tuple[list[BaseMessage], RunnableConfig | None]:
        fitted = fit_messages_to_context_budget(messages, provider_id=self.provider_id)
        return fitted, config

    def _invoke_inner(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Call wrapped model; tool bindings must use ``invoke``, not ``_generate``."""
        config: RunnableConfig | None = kwargs.pop("config", None)
        messages, config = self._prepare_messages(messages, config)
        if isinstance(self.inner, BaseChatModel):
            return self.inner._generate(
                messages,
                stop=stop,
                run_manager=run_manager,
                config=config,
                **kwargs,
            )
        ai_message = self.inner.invoke(messages, stop=stop, config=config, **kwargs)
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
        def call() -> ChatResult:
            acquire_llm_slot(self.provider_id, self.max_rpm)
            return self._invoke_inner(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )

        return invoke_with_backoff(call)

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self._unwrap_gemini_chat_model() is not None:
            import asyncio

            def call() -> ChatResult:
                acquire_llm_slot(self.provider_id, self.max_rpm)
                return self._invoke_inner(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )

            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: invoke_with_backoff(call)
            )

        def call() -> ChatResult:
            acquire_llm_slot(self.provider_id, self.max_rpm)
            return self._invoke_inner(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )

        return invoke_with_backoff(call)

    def bind_tools(self, *args: Any, **kwargs: Any) -> GuardedChatModel:
        bound = self.inner.bind_tools(*args, **kwargs)
        return self._wrap(bound)

    def with_config(self, config: RunnableConfig | None = None, **kwargs: Any) -> GuardedChatModel:
        configured = self.inner.with_config(config, **kwargs)
        return self._wrap(configured)

    def invoke(
        self,
        input: list[BaseMessage],
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AIMessage:
        def call() -> AIMessage:
            acquire_llm_slot(self.provider_id, self.max_rpm)
            fitted, run_config = self._prepare_messages(input, config)
            if isinstance(self.inner, BaseChatModel):
                result = self.inner.invoke(fitted, config=run_config, **kwargs)
            else:
                result = self.inner.invoke(fitted, config=run_config, **kwargs)
            if not isinstance(result, AIMessage):
                return AIMessage(content=str(result))
            return result

        return invoke_with_backoff(call)

    async def ainvoke(
        self,
        input: list[BaseMessage],
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AIMessage:
        """Async entry used when LangGraph streams; must not use streaming for Gemini tools."""
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.invoke(input, config=config, **kwargs)
        )
