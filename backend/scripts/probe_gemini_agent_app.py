"""Probe app get_agent_graph path."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.config import get_settings
from app.agents.context import set_agent_context, clear_agent_context
from app.agents.graph import get_agent_graph, clear_agent_graph_cache
from app.database.session import get_session_maker
from app.security.deps import CurrentUser
from app.models.enums import UserRole
from app.synthetic.generator import generate_synthetic_data
from app.synthetic.loader import load_bundle

get_settings.cache_clear()
clear_agent_graph_cache()

session = get_session_maker()()
load_bundle(session, generate_synthetic_data())
set_agent_context(session, CurrentUser(user_id=1, username="returns_analyst", role=UserRole.RETURNS_ANALYST))

graph = get_agent_graph("gemini", "returns_analyst")
try:
    out = graph.invoke(
        {
            "messages": [
                {
                    "type": "human",
                    "content": "For R105 only: call get_return_details and get_inspection_results, then one sentence summary.",
                }
            ]
        }
    )
    print("OK", len(out["messages"]))
    print(out["messages"][-1].content[:400])
except Exception as exc:
    print("FAIL", exc)
finally:
    clear_agent_context()
    session.close()
