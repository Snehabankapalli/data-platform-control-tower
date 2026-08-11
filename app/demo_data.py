from datetime import UTC, datetime

from .models import (
    AuditEvent,
    CostRecommendation,
    CostTrend,
    Incident,
    IncidentStatus,
    LineageEdge,
    LineageGraph,
    LineageNode,
    Pipeline,
    PipelineStatus,
    Severity,
)


DEMO_NOW = datetime(2026, 8, 11, 19, 20, tzinfo=UTC)


PIPELINES = (
    Pipeline(id="pipe-payments-stream", name="Payments Event Stream", domain="Payments", platform="Kafka + Spark", status=PipelineStatus.DEGRADED, freshness_minutes=12, sla_minutes=5, success_rate_percent=98.2, records_processed=84_230_551, last_run_at=DEMO_NOW, owner="Payments Data"),
    Pipeline(id="pipe-card-ledger", name="Card Ledger Daily", domain="Cards", platform="Airflow + dbt", status=PipelineStatus.HEALTHY, freshness_minutes=34, sla_minutes=60, success_rate_percent=99.8, records_processed=12_840_220, last_run_at=DEMO_NOW, owner="Core Finance"),
    Pipeline(id="pipe-fraud-features", name="Fraud Feature Pipeline", domain="Risk", platform="EMR Serverless", status=PipelineStatus.FAILED, freshness_minutes=47, sla_minutes=15, success_rate_percent=94.1, records_processed=7_402_880, last_run_at=DEMO_NOW, owner="Risk Platform"),
    Pipeline(id="pipe-claims", name="Claims Normalization", domain="Healthcare", platform="AWS Glue", status=PipelineStatus.HEALTHY, freshness_minutes=42, sla_minutes=90, success_rate_percent=99.5, records_processed=4_320_982, last_run_at=DEMO_NOW, owner="Clinical Data"),
    Pipeline(id="pipe-fhir", name="FHIR Patient Snapshot", domain="Healthcare", platform="Snowflake + dbt", status=PipelineStatus.HEALTHY, freshness_minutes=51, sla_minutes=120, success_rate_percent=99.9, records_processed=2_105_422, last_run_at=DEMO_NOW, owner="Clinical Data"),
    Pipeline(id="pipe-customer360", name="Customer 360 Incremental", domain="Growth", platform="Airflow + Snowflake", status=PipelineStatus.HEALTHY, freshness_minutes=18, sla_minutes=30, success_rate_percent=98.9, records_processed=9_881_046, last_run_at=DEMO_NOW, owner="Customer Data"),
    Pipeline(id="pipe-regulatory", name="Regulatory Reporting", domain="Compliance", platform="dbt + Snowflake", status=PipelineStatus.HEALTHY, freshness_minutes=204, sla_minutes=360, success_rate_percent=100.0, records_processed=680_412, last_run_at=DEMO_NOW, owner="Data Governance"),
    Pipeline(id="pipe-merchant", name="Merchant Settlement", domain="Payments", platform="AWS Glue + Redshift", status=PipelineStatus.HEALTHY, freshness_minutes=44, sla_minutes=60, success_rate_percent=99.4, records_processed=5_998_177, last_run_at=DEMO_NOW, owner="Payments Data"),
)


INCIDENTS = (
    Incident(
        id="inc-1042", pipeline_id="pipe-payments-stream", title="Consumer lag breached 5-minute SLA", severity=Severity.HIGH,
        status=IncidentStatus.AWAITING_APPROVAL, detected_at=datetime(2026, 8, 11, 18, 54, tzinfo=UTC),
        summary="Kafka consumer lag increased 6.4x after partition traffic skew.",
        root_cause="Two partitions receive 61% of traffic after a merchant batch replay.",
        recommended_action="Scale Spark executors from 8 to 12 for 90 minutes and rebalance partitions.",
        blast_radius="Payment analytics delayed for 3 downstream dashboards.",
        audit_log=(AuditEvent(timestamp=datetime(2026, 8, 11, 18, 55, tzinfo=UTC), actor="control-tower", action="incident_created", detail="High-severity anomaly detected from lag telemetry."),),
    ),
    Incident(
        id="inc-1043", pipeline_id="pipe-fraud-features", title="Upstream schema contract violation", severity=Severity.CRITICAL,
        status=IncidentStatus.INVESTIGATING, detected_at=datetime(2026, 8, 11, 19, 7, tzinfo=UTC),
        summary="Required transaction_country field disappeared from the upstream payload.",
        root_cause="Producer deployed schema version 42 without compatibility validation.",
        recommended_action="Quarantine version 42 events and replay after producer rollback.",
        blast_radius="Real-time fraud features are stale; fallback model remains active.",
        audit_log=(AuditEvent(timestamp=datetime(2026, 8, 11, 19, 8, tzinfo=UTC), actor="control-tower", action="incident_created", detail="Critical data contract violation detected."),),
    ),
    Incident(
        id="inc-1037", pipeline_id="pipe-claims", title="Glue worker saturation", severity=Severity.MEDIUM,
        status=IncidentStatus.RESOLVED, detected_at=datetime(2026, 8, 10, 13, 20, tzinfo=UTC),
        summary="Worker memory reached 92% during claims backfill.", root_cause="Unexpected 2.8x source volume.",
        recommended_action="Temporary G.2X worker scaling.", blast_radius="No SLA impact.", approved_by="on-call-data",
        audit_log=(AuditEvent(timestamp=datetime(2026, 8, 10, 14, 2, tzinfo=UTC), actor="on-call-data", action="incident_resolved", detail="Backfill completed and workers returned to baseline."),),
    ),
)


COST_TREND = tuple(
    CostTrend(date=date, snowflake_usd=snowflake, aws_usd=aws)
    for date, snowflake, aws in (
        ("Aug 05", 790, 565), ("Aug 06", 812, 590), ("Aug 07", 768, 548),
        ("Aug 08", 885, 624), ("Aug 09", 901, 655), ("Aug 10", 844, 603), ("Aug 11", 828, 579),
    )
)


COST_RECOMMENDATIONS = (
    CostRecommendation(id="cost-1", service="Snowflake", title="Suspend idle BI warehouse sooner", rationale="BI_WH remains idle for 41 minutes per workday; reduce auto-suspend from 10 to 2 minutes.", monthly_savings_usd=3_840, confidence_percent=96, effort="Low"),
    CostRecommendation(id="cost-2", service="AWS EMR", title="Right-size fraud feature executors", rationale="P95 executor utilization is 34%; use dynamic allocation with a lower minimum.", monthly_savings_usd=2_960, confidence_percent=88, effort="Medium"),
    CostRecommendation(id="cost-3", service="Snowflake", title="Cluster the payments fact table", rationale="Repeated 1.8 TB scans can be pruned by event_date and merchant_id.", monthly_savings_usd=1_620, confidence_percent=91, effort="Medium"),
)


LINEAGE = LineageGraph(
    nodes=(
        LineageNode(id="src-api", label="Payments API", layer="Source"), LineageNode(id="src-ledger", label="Card Ledger", layer="Source"),
        LineageNode(id="kafka", label="Kafka / payments.v3", layer="Ingest", has_incident=True), LineageNode(id="s3", label="S3 Raw Zone", layer="Storage"),
        LineageNode(id="spark", label="Spark Enrichment", layer="Transform", has_incident=True), LineageNode(id="dbt", label="dbt Core Models", layer="Transform"),
        LineageNode(id="snowflake", label="Snowflake Analytics", layer="Warehouse"), LineageNode(id="risk", label="Fraud Feature API", layer="Consumer", has_incident=True),
        LineageNode(id="bi", label="Finance BI", layer="Consumer"),
    ),
    edges=(
        LineageEdge(source="src-api", target="kafka"), LineageEdge(source="kafka", target="spark"), LineageEdge(source="spark", target="snowflake"),
        LineageEdge(source="src-ledger", target="s3"), LineageEdge(source="s3", target="dbt"), LineageEdge(source="dbt", target="snowflake"),
        LineageEdge(source="spark", target="risk"), LineageEdge(source="snowflake", target="bi"),
    ),
)

