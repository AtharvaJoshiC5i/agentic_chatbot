"""Map service error codes to HTTP status codes (shared by all routes)."""

from fastapi import status

_CONFLICT = frozenset(
    {
        "duplicate_refund",
        "duplicate_open_request",
        "duplicate_case",
        "workflow_blocked",
        "no_case",
        "verdict_required",
        "inspection_required",
        "resolution_mismatch",
        "warehouse_declined",
        "already_submitted",
        "already_sent",
        "no_stock",
        "inconsistent_verdict",
    }
)


def http_status_for(code: str | None) -> int:
    if code == "not_found":
        return status.HTTP_404_NOT_FOUND
    if code == "forbidden":
        return status.HTTP_403_FORBIDDEN
    if code in _CONFLICT:
        return status.HTTP_409_CONFLICT
    return status.HTTP_400_BAD_REQUEST
