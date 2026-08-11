from __future__ import annotations

from datetime import datetime
from threading import Lock

from . import demo_data
from .models import (
    AuditEvent,
    CostRecommendation,
    Dashboard,
    Incident,
    IncidentStatus,
    LineageGraph,
    Overview,
    Pipeline,
    PipelineStatus,
)


class ValidationError(ValueError):
    """Raised when a requested state transition is not allowed."""


class NotFoundError(LookupError):
    """Raised when a requested resource does not exist."""


class ControlTowerService:
    def __init__(
        self,
        pipelines: tuple[Pipeline, ...],
        incidents: tuple[Incident, ...],
        cost_recommendations: tuple[CostRecommendation, ...],
        lineage: LineageGraph,
    ) -> None:
        self._pipelines = pipelines
        self._incidents = incidents
        self._cost_recommendations = cost_recommendations
        self._lineage = lineage
        self._lock = Lock()

    @classmethod
    def demo(cls) -> "ControlTowerService":
        return cls(demo_data.PIPELINES, demo_data.INCIDENTS, demo_data.COST_RECOMMENDATIONS, demo_data.LINEAGE)

    def get_overview(self) -> Overview:
        active_statuses = {IncidentStatus.INVESTIGATING, IncidentStatus.AWAITING_APPROVAL, IncidentStatus.REMEDIATION_QUEUED}
        return Overview(
            total_pipelines=len(self._pipelines),
            healthy_pipelines=sum(item.status is PipelineStatus.HEALTHY for item in self._pipelines),
            active_incidents=sum(item.status in active_statuses for item in self._incidents),
            sla_compliance_percent=97.4,
            monthly_cost_usd=42_680,
            monthly_savings_opportunity_usd=sum(item.monthly_savings_usd for item in self._cost_recommendations),
            records_processed_today=sum(item.records_processed for item in self._pipelines),
        )

    def list_pipelines(self, status: str | None = None, query: str | None = None) -> tuple[Pipeline, ...]:
        normalized_status = status.lower().strip() if status else None
        valid_statuses = {item.value for item in PipelineStatus}
        if normalized_status and normalized_status not in valid_statuses:
            raise ValidationError(f"Unknown pipeline status: {status}")
        normalized_query = query.lower().strip() if query else ""
        return tuple(
            item for item in self._pipelines
            if (not normalized_status or item.status.value == normalized_status)
            and (not normalized_query or normalized_query in f"{item.name} {item.domain} {item.platform}".lower())
        )

    def list_incidents(self) -> tuple[Incident, ...]:
        return self._incidents

    def get_incident(self, incident_id: str) -> Incident:
        incident = next((item for item in self._incidents if item.id == incident_id), None)
        if incident is None:
            raise NotFoundError(f"Incident {incident_id} was not found")
        return incident

    def approve_remediation(self, incident_id: str, actor: str, now: datetime) -> Incident:
        normalized_actor = actor.strip()
        if not normalized_actor:
            raise ValidationError("Actor is required")
        with self._lock:
            incident = self.get_incident(incident_id)
            if incident.status is not IncidentStatus.AWAITING_APPROVAL:
                raise ValidationError("Incident is not awaiting approval")
            event = AuditEvent(timestamp=now, actor=normalized_actor, action="remediation_approved", detail=incident.recommended_action)
            approved = incident.model_copy(update={"status": IncidentStatus.REMEDIATION_QUEUED, "approved_by": normalized_actor, "audit_log": (*incident.audit_log, event)})
            self._incidents = tuple(approved if item.id == incident_id else item for item in self._incidents)
            return approved

    def list_cost_recommendations(self) -> tuple[CostRecommendation, ...]:
        return tuple(sorted(self._cost_recommendations, key=lambda item: item.monthly_savings_usd, reverse=True))

    def get_lineage(self) -> LineageGraph:
        return self._lineage

    def get_dashboard(self) -> Dashboard:
        return Dashboard(
            overview=self.get_overview(), pipelines=self.list_pipelines(), incidents=self.list_incidents(),
            cost_trend=demo_data.COST_TREND, cost_recommendations=self.list_cost_recommendations(), lineage=self.get_lineage(),
        )

