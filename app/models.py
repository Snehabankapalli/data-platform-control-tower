from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ImmutableModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class PipelineStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncidentStatus(StrEnum):
    INVESTIGATING = "investigating"
    AWAITING_APPROVAL = "awaiting_approval"
    REMEDIATION_QUEUED = "remediation_queued"
    RESOLVED = "resolved"


class Pipeline(ImmutableModel):
    id: str
    name: str
    domain: str
    platform: str
    status: PipelineStatus
    freshness_minutes: int = Field(ge=0)
    sla_minutes: int = Field(gt=0)
    success_rate_percent: float = Field(ge=0, le=100)
    records_processed: int = Field(ge=0)
    last_run_at: datetime
    owner: str


class Overview(ImmutableModel):
    total_pipelines: int
    healthy_pipelines: int
    active_incidents: int
    sla_compliance_percent: float
    monthly_cost_usd: int
    monthly_savings_opportunity_usd: int
    records_processed_today: int


class CostTrend(ImmutableModel):
    date: str
    snowflake_usd: int
    aws_usd: int


class CostRecommendation(ImmutableModel):
    id: str
    service: str
    title: str
    rationale: str
    monthly_savings_usd: int = Field(gt=0)
    confidence_percent: int = Field(ge=0, le=100)
    effort: str


class AuditEvent(ImmutableModel):
    timestamp: datetime
    actor: str
    action: str
    detail: str


class Incident(ImmutableModel):
    id: str
    pipeline_id: str
    title: str
    severity: Severity
    status: IncidentStatus
    detected_at: datetime
    summary: str
    root_cause: str
    recommended_action: str
    blast_radius: str
    approved_by: str | None = None
    audit_log: tuple[AuditEvent, ...] = ()


class LineageNode(ImmutableModel):
    id: str
    label: str
    layer: str
    has_incident: bool = False


class LineageEdge(ImmutableModel):
    source: str
    target: str


class LineageGraph(ImmutableModel):
    nodes: tuple[LineageNode, ...]
    edges: tuple[LineageEdge, ...]


class Dashboard(ImmutableModel):
    overview: Overview
    pipelines: tuple[Pipeline, ...]
    incidents: tuple[Incident, ...]
    cost_trend: tuple[CostTrend, ...]
    cost_recommendations: tuple[CostRecommendation, ...]
    lineage: LineageGraph


class ApprovalRequest(BaseModel):
    actor: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9 .@_-]+$")


class ApiEnvelope(BaseModel):
    success: bool
    data: object | None
    error: str | None

