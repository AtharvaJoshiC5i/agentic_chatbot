"""Return journey timeline backed by persisted return_events."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Return, ReturnEvent
from app.services.return_events import sync_return_timeline


def build_return_timeline(
    session: Session,
    return_id: str,
    *,
    sync: bool = True,
) -> list[dict]:
    """
    Chronological timeline for a return.

    By default syncs structured sources into return_events first, then reads persisted rows.
    """
    if session.get(Return, return_id) is None:
        return []

    if sync:
        sync_return_timeline(session, return_id, commit=True)

    rows = session.execute(
        select(ReturnEvent)
        .where(ReturnEvent.return_id == return_id)
        .order_by(ReturnEvent.event_timestamp, ReturnEvent.event_id)
    ).scalars().all()

    return [
        {
            "event_id": row.event_id,
            "return_id": row.return_id,
            "event_type": row.event_type,
            "event_timestamp": row.event_timestamp,
            "description": row.description,
            "source_type": row.source_type,
            "source_id": row.source_id,
        }
        for row in rows
    ]
