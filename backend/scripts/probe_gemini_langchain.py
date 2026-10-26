"""Probe LangChain GeminiChatOpenAI round-trip for thought signatures."""

from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.config import get_settings

get_settings.cache_clear()

from app.llm.gemini import get_gemini_chat_model


@tool
def get_return_details(return_id: str) -> str:
    """Get return details."""
    return f'{{"return_id":"{return_id}"}}'


model = get_gemini_chat_model().bind_tools([get_return_details])
first = model.invoke([HumanMessage(content="Call get_return_details for R105")])
print("first tool_calls", first.tool_calls)
print("additional_kwargs keys", list(first.additional_kwargs.keys()))
print("stored tool_calls", first.additional_kwargs.get("tool_calls"))
print("extras", first.additional_kwargs.get("__openai_tool_call_extras__"))

second = model.invoke(
    [
        HumanMessage(content="Call get_return_details for R105"),
        first,
        ToolMessage(content='{"return_id":"R105"}', tool_call_id=first.tool_calls[0]["id"]),
    ]
)
print("second content", (second.content or "")[:200])
