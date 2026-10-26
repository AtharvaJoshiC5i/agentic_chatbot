"""Live workflow injection for agent messages."""

from app.agents.graph import build_initial_messages
from app.models.enums import UserRole
from app.security.deps import CurrentUser


def test_build_initial_messages_includes_live_workflow(populated_db) -> None:
    user = CurrentUser(user_id=1, username="sup", role=UserRole.RETURNS_SUPERVISOR)
    messages, focus = build_initial_messages(
        "What is the status?",
        return_id="R106",
        user=user,
        db=populated_db,
    )
    assert focus == "R106"
    contents = [m.content for m in messages if hasattr(m, "content")]
    assert any("LIVE WORKFLOW SNAPSHOT" in str(c) for c in contents)
    assert any("status_summary" in str(c) for c in contents)
