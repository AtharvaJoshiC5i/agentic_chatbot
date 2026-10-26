"""Probe failure modes: chat history and streaming."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.config import get_settings
from app.agents.context import set_agent_context, clear_agent_context
from app.agents.graph import run_agent_chat, stream_agent_chat, clear_agent_graph_cache
from app.database.session import get_session_maker
from app.security.deps import CurrentUser
from app.models.enums import UserRole
from app.synthetic.generator import generate_synthetic_data
from app.synthetic.loader import load_bundle

get_settings.cache_clear()
clear_agent_graph_cache()

session = get_session_maker()()
load_bundle(session, generate_synthetic_data())
user = CurrentUser(user_id=1, username="returns_analyst", role=UserRole.RETURNS_ANALYST)
set_agent_context(session, user)

history = [
    {"role": "user", "content": "Investigate R105 briefly."},
    {"role": "assistant", "content": "R105 is a defective hub return under inspection."},
]

for label, fn in [
    ("sync_history", lambda: run_agent_chat("Now call get_return_details for R105", return_id="R105", conversation_history=history, llm_provider="gemini", db=session, user=user)),
    ("stream", lambda: list(stream_agent_chat("Call get_return_details for R105", return_id="R105", llm_provider="gemini", db=session, user=user))),
]:
    try:
        fn()
        print(label, "OK")
    except Exception as exc:
        print(label, "FAIL", str(exc)[:400])

clear_agent_context()
session.close()
