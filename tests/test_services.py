from datetime import UTC, datetime

import pytest

from app.models import IncidentStatus, Severity
from app.services import ControlTowerService, ValidationError


@pytest.fixture
def service() -> ControlTowerService:
    return ControlTowerService.demo()


def test_overview_aggregates_platform_health(service: ControlTowerService) -> None:
    overview = service.get_overview()

    assert overview.total_pipelines == 8
    assert overview.healthy_pipelines == 6
    assert overview.active_incidents == 2
    assert overview.sla_compliance_percent == 97.4
    assert overview.monthly_cost_usd == 42_680


def test_pipeline_filter_is_case_insensitive_and_does_not_mutate_state(
    service: ControlTowerService,
) -> None:
    all_before = service.list_pipelines()

    filtered = service.list_pipelines(status="DEGRADED", query="payments")

    assert [pipeline.id for pipeline in filtered] == ["pipe-payments-stream"]
    assert service.list_pipelines() == all_before


def test_cost_recommendations_are_ranked_by_savings(service: ControlTowerService) -> None:
    recommendations = service.list_cost_recommendations()

    assert [item.monthly_savings_usd for item in recommendations] == sorted(
        [item.monthly_savings_usd for item in recommendations], reverse=True
    )
    assert sum(item.monthly_savings_usd for item in recommendations) == 8_420


def test_approval_creates_new_incident_and_audit_event(service: ControlTowerService) -> None:
    original = service.get_incident("inc-1042")

    approved = service.approve_remediation(
        incident_id="inc-1042",
        actor="portfolio-reviewer",
        now=datetime(2026, 8, 11, 19, 30, tzinfo=UTC),
    )

    assert original.status is IncidentStatus.AWAITING_APPROVAL
    assert approved.status is IncidentStatus.REMEDIATION_QUEUED
    assert approved.approved_by == "portfolio-reviewer"
    assert approved.audit_log[-1].action == "remediation_approved"
    assert service.get_incident("inc-1042") == approved


def test_resolved_incident_cannot_be_approved(service: ControlTowerService) -> None:
    with pytest.raises(ValidationError, match="awaiting approval"):
        service.approve_remediation(
            incident_id="inc-1037",
            actor="portfolio-reviewer",
            now=datetime(2026, 8, 11, 19, 30, tzinfo=UTC),
        )


def test_blank_actor_is_rejected(service: ControlTowerService) -> None:
    with pytest.raises(ValidationError, match="Actor"):
        service.approve_remediation(
            incident_id="inc-1042",
            actor="   ",
            now=datetime(2026, 8, 11, 19, 30, tzinfo=UTC),
        )


def test_lineage_returns_connected_graph(service: ControlTowerService) -> None:
    graph = service.get_lineage()

    node_ids = {node.id for node in graph.nodes}
    assert len(graph.nodes) == 9
    assert all(edge.source in node_ids and edge.target in node_ids for edge in graph.edges)
    assert any(node.has_incident for node in graph.nodes)

