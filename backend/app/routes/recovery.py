"""Product recovery APIs and optimizer."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.enums import RecoveryMethod, TaskStatus
from app.models.tables import Return
from app.schemas.api import RecoveryTaskCreate, RecoveryTaskOut, RecoveryTaskPatchRequest
from app.schemas.recovery import RecoveryOptionOut, RecoveryRecommendationOut
from app.security.deps import CurrentUser, get_current_user, require_roles
from app.security.permissions import RECOVERY_TASK_ROLES
from app.services.recovery import (
    RecoveryServiceError,
    create_recovery_task,
    create_task_from_recommendation,
)
from app.services.recovery_optimizer import RecoveryOptimizerError, list_recovery_options, optimize_recovery
from app.services.recovery_tasks import (
    RecoveryTaskServiceError,
    list_recovery_tasks,
    update_recovery_task,
)

router = APIRouter(prefix="/recovery")


@router.get("/tasks", response_model=list[RecoveryTaskOut])
def get_recovery_tasks(
    status_filter: str | None = Query(None, alias="status"),
    assigned_to: str | None = Query(None),
    return_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_roles(*RECOVERY_TASK_ROLES)),
) -> list[RecoveryTaskOut]:
    rows = list_recovery_tasks(
        db,
        status=status_filter,
        assigned_to=assigned_to,
        return_id=return_id,
        limit=limit,
    )
    return [RecoveryTaskOut.model_validate(row) for row in rows]


@router.patch("/tasks/{task_id}", response_model=RecoveryTaskOut)
def patch_recovery_task(
    task_id: int,
    payload: RecoveryTaskPatchRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*RECOVERY_TASK_ROLES)),
) -> RecoveryTaskOut:
    task_status = None
    if payload.task_status:
        try:
            task_status = TaskStatus(payload.task_status.strip().lower())
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task_status") from exc
    try:
        task = update_recovery_task(
            db,
            task_id,
            assigned_to=payload.assigned_to,
            task_status=task_status,
            actor=user,
        )
    except RecoveryTaskServiceError as exc:
        code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return RecoveryTaskOut.model_validate(task)



@router.get("/returns/{return_id}/options", response_model=list[RecoveryOptionOut])
def get_recovery_options(
    return_id: str,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> list[RecoveryOptionOut]:
    if db.get(Return, return_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found")
    rows = list_recovery_options(db, return_id)
    return [RecoveryOptionOut.model_validate(row) for row in rows]


@router.get("/returns/{return_id}/recommendation", response_model=RecoveryRecommendationOut)
def get_recovery_recommendation(
    return_id: str,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> RecoveryRecommendationOut:
    try:
        recommendation = optimize_recovery(db, return_id)
    except RecoveryOptimizerError as exc:
        code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return RecoveryRecommendationOut.model_validate(recommendation.to_dict())


@router.post("/tasks", response_model=RecoveryTaskOut, status_code=status.HTTP_201_CREATED)
def post_recovery_task(
    payload: RecoveryTaskCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*RECOVERY_TASK_ROLES)),
) -> RecoveryTaskOut:
    try:
        task = create_recovery_task(
            db,
            return_id=payload.return_id,
            recovery_method=payload.recovery_method,
            assigned_to=payload.assigned_to,
            actor=user,
        )
    except RecoveryServiceError as exc:
        code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return RecoveryTaskOut.model_validate(task)


@router.post("/returns/{return_id}/tasks/from-recommendation", response_model=RecoveryTaskOut)
def post_recovery_task_from_recommendation(
    return_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*RECOVERY_TASK_ROLES)),
    assigned_to: str | None = Query(None),
    recovery_method: RecoveryMethod | None = Query(None),
    allow_non_recommended: bool = Query(False),
) -> RecoveryTaskOut:
    try:
        task = create_task_from_recommendation(
            db,
            return_id=return_id,
            assigned_to=assigned_to,
            actor=user,
            allow_non_recommended=allow_non_recommended,
            recovery_method=recovery_method,
        )
    except RecoveryServiceError as exc:
        code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return RecoveryTaskOut.model_validate(task)
