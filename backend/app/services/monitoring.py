"""Operational monitoring checks (F8) → system_alerts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    ApprovalStatus,
    CaseStatus,
    ExecutionStatus,
    IssueType,
    ReturnStatus,
    TaskStatus,
)
from app.models.tables import (
    ActionRequest,
    Inspection,
    InvestigationCase,
    Refund,
    RecoveryTask,
    MonitoringRun,
    Return,
    SystemAlert,
)
from sqlalchemy import func

from app.services.alerts import AlertFinding, list_alerts, resolve_inactive_open_alerts, upsert_open_alert
from app.services.escalations import create_escalation


RECOVERY_OVERDUE_DAYS = 7


@dataclass
class MonitoringRunResult:
    findings_count: int
    alerts_created: int
    alerts_resolved: int
    open_alerts: int
    by_type: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "findings_count": self.findings_count,
            "alerts_created": self.alerts_created,
            "alerts_resolved": self.alerts_resolved,
            "open_alerts": self.open_alerts,
            "by_type": self.by_type,
        }


def collect_findings(session: Session) -> list[AlertFinding]:
    now = utc_now()
    findings: list[AlertFinding] = []

    overdue_cases = session.execute(
        select(InvestigationCase).where(
            InvestigationCase.due_date.is_not(None),
            InvestigationCase.due_date < now,
            InvestigationCase.case_status.not_in([CaseStatus.RESOLVED.value, CaseStatus.CLOSED.value]),
        )
    ).scalars().all()
    for case in overdue_cases:
        findings.append(
            AlertFinding(
                AlertType.OVERDUE_INVESTIGATION,
                "investigation_case",
                str(case.case_id),
                AlertSeverity.HIGH,
            )
        )

    pending_refunds = session.execute(
        select(Refund).where(Refund.approval_status == ApprovalStatus.PENDING.value)
    ).scalars().all()
    for refund in pending_refunds:
        findings.append(
            AlertFinding(
                AlertType.PENDING_REFUND_APPROVAL,
                "refund",
                str(refund.refund_id),
                AlertSeverity.WARNING,
            )
        )

    failed_actions = session.execute(
        select(ActionRequest).where(ActionRequest.execution_status == ExecutionStatus.FAILED.value)
    ).scalars().all()
    for action in failed_actions:
        findings.append(
            AlertFinding(
                AlertType.FAILED_ACTION,
                "action_request",
                str(action.action_id),
                AlertSeverity.HIGH,
            )
        )

    recovery_cutoff = now - timedelta(days=RECOVERY_OVERDUE_DAYS)
    overdue_tasks = session.execute(
        select(RecoveryTask).where(
            RecoveryTask.created_at < recovery_cutoff,
            RecoveryTask.task_status.in_(
                [
                    TaskStatus.PENDING.value,
                    TaskStatus.ASSIGNED.value,
                    TaskStatus.IN_PROGRESS.value,
                ]
            ),
        )
    ).scalars().all()
    for task in overdue_tasks:
        findings.append(
            AlertFinding(
                AlertType.OVERDUE_RECOVERY_TASK,
                "recovery_task",
                str(task.recovery_task_id),
                AlertSeverity.WARNING,
            )
        )

    received_returns = session.execute(
        select(Return).where(
            Return.received_date.is_not(None),
            Return.return_status.in_(
                [
                    ReturnStatus.RECEIVED.value,
                    ReturnStatus.INSPECTING.value,
                ]
            ),
        )
    ).scalars().all()
    for return_row in received_returns:
        inspection_count = session.execute(
            select(func.count())
            .select_from(Inspection)
            .where(Inspection.return_id == return_row.return_id)
        ).scalar_one()
        if inspection_count == 0:
            findings.append(
                AlertFinding(
                    AlertType.AWAITING_INSPECTION,
                    "return",
                    return_row.return_id,
                    AlertSeverity.WARNING,
                )
            )

    inconsistency_cases = session.execute(
        select(InvestigationCase).where(
            InvestigationCase.case_status.not_in([CaseStatus.RESOLVED.value, CaseStatus.CLOSED.value]),
            InvestigationCase.issue_type.in_(
                [
                    IssueType.SERIAL_MISMATCH.value,
                    IssueType.CONFLICTING_EVIDENCE.value,
                    IssueType.PRODUCT_MISMATCH.value,
                    IssueType.SAFETY_CONCERN.value,
                ]
            ),
        )
    ).scalars().all()
    for case in inconsistency_cases:
        findings.append(
            AlertFinding(
                AlertType.UNRESOLVED_INCONSISTENCY,
                "return",
                case.return_id,
                AlertSeverity.HIGH if case.issue_type == IssueType.SAFETY_CONCERN.value else AlertSeverity.WARNING,
            )
        )

    return findings


def run_monitoring_checks(session: Session, *, commit: bool = True) -> MonitoringRunResult:
    started_at = utc_now()
    findings = collect_findings(session)
    created = 0
    for finding in findings:
        before = session.execute(
            select(SystemAlert.alert_id).where(
                SystemAlert.alert_type == finding.alert_type.value,
                SystemAlert.related_entity == finding.related_entity,
                SystemAlert.related_id == finding.related_id,
                SystemAlert.status == AlertStatus.OPEN.value,
            )
        ).scalar_one_or_none()
        upsert_open_alert(session, finding)
        after = session.execute(
            select(SystemAlert.alert_id).where(
                SystemAlert.alert_type == finding.alert_type.value,
                SystemAlert.related_entity == finding.related_entity,
                SystemAlert.related_id == finding.related_id,
                SystemAlert.status == AlertStatus.OPEN.value,
            )
        ).scalar_one_or_none()
        if before is None and after is not None:
            created += 1
        if finding.alert_type in {AlertType.OVERDUE_INVESTIGATION, AlertType.OVERDUE_RECOVERY_TASK}:
            create_escalation(
                session,
                related_entity=finding.related_entity,
                related_id=finding.related_id,
                escalation_reason=finding.alert_type.value,
                owner_username=None,
                commit=False,
            )

    resolved = resolve_inactive_open_alerts(session, findings)
    finished_at = utc_now()
    run_row = MonitoringRun(
        started_at=started_at,
        finished_at=finished_at,
        findings_count=len(findings),
        summary_json=json.dumps(
            {"alerts_created": created, "findings": len(findings)},
            default=str,
        ),
    )
    session.add(run_row)
    if commit:
        session.commit()

    open_count = session.execute(
        select(func.count()).select_from(SystemAlert).where(SystemAlert.status == AlertStatus.OPEN.value)
    ).scalar_one()
    by_type: dict[str, int] = {}
    rows = session.execute(
        select(SystemAlert.alert_type, func.count())
        .where(SystemAlert.status == AlertStatus.OPEN.value)
        .group_by(SystemAlert.alert_type)
    ).all()
    for alert_type, count in rows:
        by_type[str(alert_type)] = int(count)

    return MonitoringRunResult(
        findings_count=len(findings),
        alerts_created=created,
        alerts_resolved=resolved,
        open_alerts=int(open_count),
        by_type=by_type,
    )


def get_monitoring_summary(session: Session) -> dict[str, Any]:
    """Read-only snapshot of open alerts. Use run_monitoring_checks via POST /monitoring/run to refresh."""
    open_alerts = list_alerts(session, status=AlertStatus.OPEN.value, limit=200)
    return {
        "open_alerts": len(open_alerts),
        "alerts": [
            {
                "alert_id": row.alert_id,
                "alert_type": row.alert_type,
                "severity": row.severity,
                "status": row.status,
                "related_entity": row.related_entity,
                "related_id": row.related_id,
                "created_at": row.created_at,
            }
            for row in open_alerts
        ],
    }
