"""Agent capability discovery for the UI."""

from fastapi import APIRouter

from app.agents.capabilities import AgentCapabilityOut, AGENT_CAPABILITIES

router = APIRouter(prefix="/agent")


@router.get("/capabilities", response_model=list[AgentCapabilityOut])
def get_agent_capabilities() -> list[AgentCapabilityOut]:
    """What the chat agent can do: tools, examples, and when to use each."""
    return AGENT_CAPABILITIES
