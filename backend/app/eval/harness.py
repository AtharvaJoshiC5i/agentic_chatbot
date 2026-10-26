"""Run API-level ground-truth evaluation without calling external LLMs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.eval.loaders import load_expected_decisions, load_expected_tool_actions, load_return_scenarios_csv
from app.eval.registry import registered_tool_names, resolve_tool_name
from app.investigation.investigation import run_investigation
from app.models.enums import AlertType, IssueType, RecoveryMethod, RefundStatus, UserRole
from app.models.tables import Inspection, Refund
from app.services.escalations import create_escalation
from app.services.monitoring import collect_findings, run_monitoring_checks
from app.services.cases import create_case, get_active_case
from app.security.deps import CurrentUser
from app.services.recovery_optimizer import optimize_recovery
from app.services.refunds import get_refund_for_return
from fastapi.testclient import TestClient

from app.main import app
from app.synthetic.scenarios import SCENARIO_BY_RETURN_ID, SCENARIO_SPECS


@dataclass
class EvalCheck:
    check_id: str
    passed: bool
    detail: str


@dataclass
class EvalReport:
    checks: list[EvalCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def failed(self) -> list[EvalCheck]:
        return [check for check in self.checks if not check.passed]

    def add(self, check_id: str, passed: bool, detail: str) -> None:
        self.checks.append(EvalCheck(check_id=check_id, passed=passed, detail=detail))

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "total": len(self.checks),
            "failed": len(self.failed),
            "checks": [
                {"check_id": c.check_id, "passed": c.passed, "detail": c.detail} for c in self.checks
            ],
        }


def _check_repo_ground_truth_files(report: EvalReport) -> None:
    decisions = load_expected_decisions()
    for spec in SCENARIO_SPECS:
        entry = decisions.get(spec.return_id)
        ok = (
            entry is not None
            and entry["expected_investigation_outcome"] == spec.expected_investigation_outcome
            and entry["expected_signal"] == spec.expected_signal
        )
        report.add(
            f"repo_decisions_{spec.return_id}",
            ok,
            "expected_decisions.json matches scenario spec"
            if ok
            else f"mismatch for {spec.return_id}",
        )

    rows = load_return_scenarios_csv()
    csv_ids = {row["return_id"] for row in rows}
    spec_ids = {spec.return_id for spec in SCENARIO_SPECS}
    report.add(
        "repo_return_scenarios_csv",
        csv_ids == spec_ids,
        f"return_scenarios.csv covers {len(csv_ids)} scenario returns",
    )


def _check_tool_catalog(report: EvalReport) -> None:
    tools = registered_tool_names()
    actions = load_expected_tool_actions()
    for return_id, spec in actions.items():
        for tool_name in spec.get("expected_tools", []):
            resolved = resolve_tool_name(tool_name)
            report.add(
                f"tool_catalog_expected_{return_id}_{tool_name}",
                resolved in tools,
                f"{tool_name} resolves to {resolved}",
            )
        for tool_name in spec.get("must_not", []):
            resolved = resolve_tool_name(tool_name)
            report.add(
                f"tool_catalog_must_not_{return_id}_{tool_name}",
                resolved in tools,
                f"must_not tool {tool_name} resolves to {resolved}",
            )


def _check_investigation_engine(session: Session, report: EvalReport) -> None:
    decisions = load_expected_decisions()
    for return_id, expected in decisions.items():
        result = run_investigation(session, return_id)
        report.add(
            f"investigation_outcome_{return_id}",
            result is not None and result.f4_outcome == expected["expected_investigation_outcome"],
            f"{return_id} outcome {result.f4_outcome if result else None}",
        )
        if result is not None:
            report.add(
                f"investigation_signal_{return_id}",
                result.f2_signal == expected["expected_signal"],
                f"{return_id} signal {result.f2_signal}",
            )

    tool_actions = load_expected_tool_actions()
    for return_id, spec in tool_actions.items():
        if "expected_signal" in spec and return_id in decisions:
            result = run_investigation(session, return_id)
            if result:
                report.add(
                    f"tool_actions_signal_{return_id}",
                    result.f2_signal == spec["expected_signal"],
                    f"signal {result.f2_signal}",
                )


def _check_structured_fixtures(session: Session, report: EvalReport) -> None:
    r106_completed = session.execute(
        select(func.count())
        .select_from(Refund)
        .where(Refund.return_id == "R106", Refund.refund_status == RefundStatus.COMPLETED.value)
    ).scalar_one()
    report.add("fixture_r106_single_completed_refund", r106_completed == 1, f"count={r106_completed}")

    r113_inspections = session.execute(
        select(func.count()).select_from(Inspection).where(Inspection.return_id == "R113")
    ).scalar_one()
    report.add("fixture_r113_no_inspection", r113_inspections == 0, f"count={r113_inspections}")

    r110_inspections = session.execute(
        select(func.count()).select_from(Inspection).where(Inspection.return_id == "R110")
    ).scalar_one()
    report.add("fixture_r110_multiple_inspections", r110_inspections >= 2, f"count={r110_inspections}")


def _check_recovery_optimizer(session: Session, report: EvalReport) -> None:
    r108 = optimize_recovery(session, "R108")
    report.add(
        "recovery_r108_repair_resell",
        r108.recommended_method == RecoveryMethod.REPAIR_RESELL.value,
        f"recommended={r108.recommended_method}",
    )
    r115 = optimize_recovery(session, "R115")
    report.add("recovery_r115_unsafe", r115.unsafe_product is True, "unsafe flag")
    report.add(
        "recovery_r115_no_resell_recommendation",
        r115.recommended_method not in {"resell_new", "open_box_resale", "repair_and_resell", "refurbish_and_resell"},
        f"recommended={r115.recommended_method}",
    )


def _check_monitoring_findings(session: Session, report: EvalReport) -> None:
    findings = collect_findings(session)
    report.add(
        "monitoring_r113_awaiting_inspection",
        any(
            f.alert_type == AlertType.AWAITING_INSPECTION and f.related_id == "R113" for f in findings
        ),
        "R113 awaiting inspection alert",
    )


def _check_demo_scenarios_api(session: Session, report: EvalReport) -> None:
    """Demo scenarios A–E: high-level API contracts (no LLM)."""
    client = TestClient(app)

    # A — valid return investigation
    spec_a = SCENARIO_BY_RETURN_ID["R101"]
    inv_a = run_investigation(session, "R101")
    report.add(
        "demo_A_valid_return",
        inv_a is not None and inv_a.f4_outcome == spec_a.expected_investigation_outcome,
        spec_a.title,
    )

    # B — serial mismatch
    inv_b = run_investigation(session, "R102")
    report.add(
        "demo_B_serial_mismatch",
        inv_b is not None and inv_b.f2_signal == "additional_verification_required",
        "R102 verification signal",
    )

    # C — duplicate refund path (completed refund exists)
    refund = get_refund_for_return(session, "R106")
    report.add(
        "demo_C_already_refunded",
        refund is not None and refund.refund_status == RefundStatus.COMPLETED.value,
        "R106 completed refund",
    )

    # D — repairable laptop recovery
    rec_d = optimize_recovery(session, "R108")
    report.add(
        "demo_D_repairable_product",
        rec_d.recommended_method == RecoveryMethod.REPAIR_RESELL.value,
        "R108 repair recommendation",
    )

    # E — unsafe product disposition
    rec_e = optimize_recovery(session, "R115")
    report.add(
        "demo_E_unsafe_product",
        rec_e.unsafe_product and rec_e.recommended_method in {"dispose", "recycle", "supplier_return"},
        "R115 safe disposition",
    )

    # Health endpoint smoke
    health = client.get("/api/health")
    report.add("demo_api_health", health.status_code == 200, f"status={health.status_code}")


def _check_escalation_dedup(session: Session, report: EvalReport) -> None:
    a = create_escalation(session, related_entity="return", related_id="R108", escalation_reason="test_dedup")
    b = create_escalation(session, related_entity="return", related_id="R108", escalation_reason="test_dedup")
    report.add("escalation_dedup", a.escalation_id == b.escalation_id, "open escalation dedup")


def _check_duplicate_case_guard(session: Session, report: EvalReport) -> None:
    actor = CurrentUser(user_id=0, username="eval", role=UserRole.RETURNS_ANALYST)
    first = create_case(session, return_id="R104", issue_type=IssueType.DELIVERY_DISPUTE, priority="medium", actor=actor)
    second = create_case(session, return_id="R104", issue_type=IssueType.GENERAL, priority="low", actor=actor)
    report.add(
        "case_duplicate_reuse",
        second.case_id == first.case_id and get_active_case(session, "R104") is not None,
        "active case reused",
    )


def _check_monitoring_run_logged(session: Session, report: EvalReport) -> None:
    from app.models.tables import MonitoringRun
    from sqlalchemy import func, select

    before = session.execute(select(func.count()).select_from(MonitoringRun)).scalar_one()
    run_monitoring_checks(session, commit=True)
    after = session.execute(select(func.count()).select_from(MonitoringRun)).scalar_one()
    report.add("monitoring_run_persisted", after > before, f"runs {before}->{after}")


def run_full_eval(session: Session) -> EvalReport:
    report = EvalReport()
    _check_repo_ground_truth_files(report)
    _check_tool_catalog(report)
    _check_structured_fixtures(session, report)
    _check_investigation_engine(session, report)
    _check_recovery_optimizer(session, report)
    _check_monitoring_findings(session, report)
    _check_demo_scenarios_api(session, report)
    _check_escalation_dedup(session, report)
    _check_duplicate_case_guard(session, report)
    _check_monitoring_run_logged(session, report)
    return report
