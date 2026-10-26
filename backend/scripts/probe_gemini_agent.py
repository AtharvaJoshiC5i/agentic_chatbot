"""Probe create_react_agent + Gemini through full graph."""

from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.config import get_settings

get_settings.cache_clear()

from app.llm.gemini import get_gemini_chat_model


@tool
def get_return_details(return_id: str) -> str:
    """Get return details."""
    return f'{{"return_id":"{return_id}","status":"received"}}'


@tool
def get_inspection_results(return_id: str) -> str:
    """Get inspections."""
    return "[]"


model = get_gemini_chat_model().bind_tools([get_return_details, get_inspection_results])
graph = create_react_agent(model, [get_return_details, get_inspection_results])

try:
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="For R105 call get_return_details and get_inspection_results then summarize."
                )
            ]
        }
    )
    print("OK messages", len(result["messages"]))
    print("last", result["messages"][-1].content[:300])
except Exception as exc:
    print("FAIL", exc)
