"""Agent chat API (Groq or Gemini + LangGraph)."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents.context import clear_agent_context
from app.agents.graph import run_agent_chat, sse_encode, stream_agent_chat
from app.database.session import get_db
from app.llm.router import is_provider_configured, model_name_for, normalize_provider
from app.schemas.chat import (
    AgentStepOut,
    ChatRequest,
    ChatResponse,
    DocumentSourceOut,
    StructuredEvidenceOut,
    SupportingEvidenceOut,
)
from app.security.deps import CurrentUser, get_current_user

router = APIRouter(prefix="/chat")


@router.post("", response_model=ChatResponse)
def post_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ChatResponse:
    try:
        provider = normalize_provider(payload.llm_provider)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not is_provider_configured(provider):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"LLM provider '{provider}' is not configured. "
                "Set GROQ_API_KEY / GROQ_MODEL, GEMINI_API_KEY, or NVIDIA_API_KEY in .env"
            ),
        )

    try:
        result = run_agent_chat(
            payload.message,
            return_id=payload.return_id,
            conversation_history=[turn.model_dump() for turn in payload.history],
            llm_provider=provider,
            db=db,
            user=user,
        )
    except Exception as exc:  # noqa: BLE001 — return safe API error for upstream LLM failures
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Agent execution failed: {exc}",
        ) from exc
    finally:
        clear_agent_context()

    evidence_raw = result.get("supporting_evidence") or {"structured": [], "documents": []}
    supporting = SupportingEvidenceOut(
        structured=[StructuredEvidenceOut.model_validate(s) for s in evidence_raw.get("structured", [])],
        documents=[DocumentSourceOut.model_validate(d) for d in evidence_raw.get("documents", [])],
    )

    return ChatResponse(
        conversation_id=payload.conversation_id,
        return_id=payload.return_id or result.get("inferred_return_id"),
        inferred_return_id=result.get("inferred_return_id"),
        final_response=result["final_response"],
        tool_events=result["tool_events"],
        agent_steps=[AgentStepOut.model_validate(s) for s in result.get("agent_steps") or []],
        supporting_evidence=supporting,
        document_sources=supporting.documents,
        visuals=result.get("visuals") or [],
        llm_provider=provider,
        llm_model=model_name_for(provider),
    )


@router.post("/stream")
def post_chat_stream(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    try:
        provider = normalize_provider(payload.llm_provider)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not is_provider_configured(provider):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"LLM provider '{provider}' is not configured. "
                "Set GROQ_API_KEY / GROQ_MODEL or GEMINI_API_KEY in .env"
            ),
        )

    def event_generator():
        try:
            for item in stream_agent_chat(
                payload.message,
                return_id=payload.return_id,
                conversation_history=[turn.model_dump() for turn in payload.history],
                llm_provider=provider,
                db=db,
                user=user,
            ):
                event = item.get("event", "message")
                data = item.get("data", {})
                if event == "done":
                    data = {
                        **data,
                        "conversation_id": payload.conversation_id,
                        "return_id": payload.return_id or data.get("inferred_return_id"),
                        "llm_provider": provider,
                        "llm_model": model_name_for(provider),
                    }
                yield sse_encode(event, data)
        except Exception as exc:  # noqa: BLE001
            yield sse_encode("error", {"detail": f"Agent execution failed: {exc}"})
        finally:
            clear_agent_context()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
