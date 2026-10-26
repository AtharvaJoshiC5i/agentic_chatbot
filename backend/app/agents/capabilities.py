"""Human-readable catalog of what the returns agent can do (for API + UI)."""

from pydantic import BaseModel, Field


class AgentCapabilityOut(BaseModel):
    id: str
    title: str
    description: str
    example_prompt: str
    tools: list[str] = Field(default_factory=list)
    return_id_hint: str | None = None


AGENT_CAPABILITIES: list[AgentCapabilityOut] = [
    AgentCapabilityOut(
        id="investigate",
        title="Investigate a return",
        description=(
            "Eligibility, policy window, warehouse findings, and a plain-language recommendation—"
            "refund, escalate, or verify."
        ),
        example_prompt="Investigate return R102 and tell me in plain language if we should refund, escalate, or verify further.",
        tools=["run_return_investigation"],
        return_id_hint="R102",
    ),
    AgentCapabilityOut(
        id="lookup",
        title="Look up shop records",
        description=(
            "Order, delivery, product, inspection, refund status, and customer return history in one place."
        ),
        example_prompt="Pull full details for return R106 including refund status.",
        tools=[
            "get_return_details",
            "get_order_details",
            "get_inspection_results",
            "get_refund_status",
        ],
        return_id_hint="R106",
    ),
    AgentCapabilityOut(
        id="documents",
        title="Search policies & communications",
        description=(
            "Complaints, support emails, inspection PDFs, warranty text, and the return policy that applies."
        ),
        example_prompt="Search complaints about serial verification for R102.",
        tools=["search_customer_complaints", "search_return_policy", "resolve_applicable_policy"],
        return_id_hint="R102",
    ),
    AgentCapabilityOut(
        id="recovery",
        title="Recommend product recovery",
        description=(
            "Compare repair, refurbish, resale, and disposal by net value—with safety rules for damaged goods."
        ),
        example_prompt="What recovery do you recommend for R108?",
        tools=["get_recovery_options", "get_recovery_recommendation"],
        return_id_hint="R108",
    ),
    AgentCapabilityOut(
        id="actions",
        title="Submit operational actions",
        description=(
            "Open a case, request a refund, or create a recovery task. "
            "Supervisor approval applies where required."
        ),
        example_prompt="Open an investigation case for R103 if outside policy.",
        tools=["submit_create_investigation_case", "submit_refund_request", "submit_repair_recovery_task"],
        return_id_hint="R103",
    ),
]


def list_capabilities() -> list[dict[str, object]]:
    return [c.model_dump() for c in AGENT_CAPABILITIES]
