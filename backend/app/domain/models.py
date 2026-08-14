"""
Pydantic Domain Models / Schemas

These are the strongly-typed Pydantic v2 models used across the application
for API request/response validation and internal domain modeling.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ─── Enums ────────────────────────────────────────────────────────────────────

class TargetStatus(str, Enum):
    registered = "registered"
    active = "active"
    inactive = "inactive"
    archived = "archived"


class AdapterType(str, Enum):
    rest = "rest"
    openai_compatible = "openai_compatible"
    local_python = "local_python"
    langchain = "langchain"
    mock = "mock"


class RunStatus(str, Enum):
    registered = "registered"
    planned = "planned"
    running = "running"
    awaiting_telemetry = "awaiting_telemetry"
    evaluating = "evaluating"
    evidence_ready = "evidence_ready"
    reported = "reported"
    failed = "failed"
    cancelled = "cancelled"


class PipelineType(str, Enum):
    direct = "direct"
    indirect = "indirect"
    multiturn = "multiturn"
    tool_output = "tool_output"


class SeverityLevel(str, Enum):
    informational = "informational"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class FindingStatus(str, Enum):
    open = "open"
    triaged = "triaged"
    confirmed = "confirmed"
    false_positive = "false_positive"
    accepted_risk = "accepted_risk"
    resolved = "resolved"


class InstructionOrigin(str, Enum):
    system = "system"
    developer = "developer"
    user = "user"
    retrieved_content = "retrieved_content"
    document = "document"
    tool_output = "tool_output"
    previous_agent_output = "previous_agent_output"
    external_api = "external_api"


class EventType(str, Enum):
    session_started = "SESSION_STARTED"
    session_ended = "SESSION_ENDED"
    input = "INPUT"
    response = "RESPONSE"
    tool_call = "TOOL_CALL"
    tool_result = "TOOL_RESULT"
    artifact_created = "ARTIFACT_CREATED"
    artifact_retrieved = "ARTIFACT_RETRIEVED"
    evaluation = "EVALUATION"
    authorization_check = "AUTHORIZATION_CHECK"
    error = "ERROR"


class SignalType(str, Enum):
    unauthorized_tool_call = "unauthorized_tool_call"
    unauthorized_data_access = "unauthorized_data_access"
    secret_disclosure = "secret_disclosure"
    instruction_hierarchy_violation = "instruction_hierarchy_violation"
    injected_content_triggered_action = "injected_content_triggered_action"
    tool_output_instruction_following = "tool_output_instruction_following"
    task_deviation = "task_deviation"
    chained_unauthorized_action = "chained_unauthorized_action"


class ArtifactFormat(str, Enum):
    pdf = "pdf"
    txt = "txt"
    markdown = "markdown"
    html = "html"
    csv = "csv"
    json = "json"
    email = "email"


# ─── Target Models ────────────────────────────────────────────────────────────

class TargetCapability(BaseModel):
    name: str
    description: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    is_destructive: bool = False
    privilege_level: str = "standard"
    category: str | None = None


class Target(BaseModel):
    id: str
    name: str
    description: str | None = None
    adapter_type: AdapterType
    endpoint_url: str | None = None
    model_name: str | None = None
    adapter_config: dict[str, Any] = Field(default_factory=dict)
    status: TargetStatus = TargetStatus.registered
    tags: list[str] = Field(default_factory=list)
    capabilities: list[TargetCapability] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    last_assessed_at: datetime | None = None

    model_config = {"from_attributes": True}


class TargetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    adapter_type: AdapterType
    endpoint_url: str | None = None
    model_name: str | None = None
    adapter_config: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


# ─── Authorization Models ─────────────────────────────────────────────────────

class AuthorizationRecord(BaseModel):
    id: str
    target_id: str
    authorized_by: str
    scope: dict[str, Any]
    allowed_tools: list[str]
    allowed_pipelines: list[str]
    valid_from: datetime
    valid_until: datetime | None = None
    authorization_document: str | None = None
    authorization_reference: str | None = None
    status: str
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthorizationCreate(BaseModel):
    target_id: str
    authorized_by: str = Field(..., min_length=1)
    scope: dict[str, Any] = Field(default_factory=dict)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_pipelines: list[str] = Field(default_factory=list)
    valid_from: datetime
    valid_until: datetime | None = None
    authorization_document: str | None = None
    authorization_reference: str | None = None
    notes: str | None = None


# ─── Payload Models ────────────────────────────────────────────────────────────

class Payload(BaseModel):
    """Immutable payload record."""
    payload_id: str  # SHA-256 of realized content
    family: str
    attack_type: str
    objective: str
    base_template: str
    realized_content: str
    mutation_strategy: str | None = None
    mutation_seed: int | None = None
    encoding: str | None = None
    language: str = "en"
    pipeline_compatibility: list[str] = Field(default_factory=list)
    expected_signal: str | None = None
    expected_impact: str | None = None
    severity_prior: SeverityLevel = SeverityLevel.medium
    source: str = "deterministic"
    license: str = "research-only"
    created_at: datetime

    model_config = {"from_attributes": True}


class PayloadGenerateRequest(BaseModel):
    family: str
    attack_type: str | None = None
    objective: str
    pipeline: PipelineType | None = None
    mutation_strategy: str | None = None
    mutation_seed: int | None = None
    encoding: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    count: int = Field(default=1, ge=1, le=50)


# ─── Run Models ───────────────────────────────────────────────────────────────

class RunCreate(BaseModel):
    target_id: str
    authorization_id: str | None = None
    name: str = Field(..., min_length=1, max_length=512)
    description: str | None = None
    pipelines: list[PipelineType] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    payload_families: list[str] = Field(default_factory=list)
    risk_limits: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)


class Run(BaseModel):
    id: str
    target_id: str
    authorization_id: str | None
    name: str
    description: str | None
    status: RunStatus
    pipelines: list[str]
    objectives: list[str]
    total_test_cases: int
    completed_test_cases: int
    findings_count: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    attack_success_rate: float | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Test Plan Models ─────────────────────────────────────────────────────────

class TestCase(BaseModel):
    id: str
    test_plan_id: str
    pipeline: str
    payload_id: str | None
    objective: str
    description: str | None
    control_required: bool
    expected_signal: str | None
    risk_level: str
    timeout_seconds: int
    max_turns: int
    status: str
    result: str | None
    config: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class TestPlan(BaseModel):
    id: str
    run_id: str
    name: str
    status: str
    test_cases: list[TestCase] = Field(default_factory=list)
    generated_at: datetime
    approved_at: datetime | None

    model_config = {"from_attributes": True}


# ─── Telemetry Models ─────────────────────────────────────────────────────────

class TelemetryEvent(BaseModel):
    id: str
    run_id: str
    session_id: str | None
    turn_number: int | None
    sequence_number: int
    event_type: EventType
    payload_id: str | None
    artifact_id: str | None
    call_id: str | None
    payload_data: dict[str, Any]
    origin: InstructionOrigin | None
    event_hash: str | None
    previous_event_hash: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}


class InstructionSpan(BaseModel):
    span_id: str
    run_id: str
    session_id: str
    source_event_id: str | None
    origin: InstructionOrigin
    content_hash: str
    content_preview: str | None
    start_offset: int | None
    end_offset: int | None
    triggered_tool_call_id: str | None
    triggered_event_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Evaluation Models ────────────────────────────────────────────────────────

class EvaluationSignal(BaseModel):
    signal_type: SignalType
    source: str  # deterministic|llm_judge
    confidence: float = Field(ge=0.0, le=1.0)
    severity_contribution: float = Field(ge=0.0)
    rationale: str
    evidence_event_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgenticRiskScore(BaseModel):
    """Explainable AgenticRiskScore breakdown."""
    impact_weight: float
    tool_privilege_weight: float
    data_sensitivity_weight: float
    exploit_reliability: float
    propagation_factor: float
    persistence_factor: float = 1.0
    causal_confidence: float
    raw_score: float
    normalized_score: float  # 0.0 - 10.0
    severity: SeverityLevel
    breakdown: dict[str, Any] = Field(default_factory=dict)


# ─── Finding Models ───────────────────────────────────────────────────────────

class Finding(BaseModel):
    id: str
    run_id: str
    session_id: str | None
    title: str
    description: str
    severity: SeverityLevel
    risk_score: float
    risk_score_breakdown: dict[str, Any]
    pipeline: str
    objective: str
    payload_id: str | None
    artifact_id: str | None
    confidence: float
    status: FindingStatus
    attack_path: list[str]
    evidence_ids: list[str]
    deterministic_signals: list[dict]
    llm_judge_result: dict[str, Any]
    reproduction_steps: list[str]
    remediation: str | None
    references: list[str]
    affected_target: str | None
    affected_tool: str | None
    first_seen: datetime
    last_seen: datetime

    model_config = {"from_attributes": True}


# ─── Report Models ────────────────────────────────────────────────────────────

class Report(BaseModel):
    id: str
    run_id: str
    name: str
    status: str
    json_path: str | None
    html_path: str | None
    pdf_path: str | None
    llm_available: bool
    findings_count: int
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


# ─── Experiment Models ────────────────────────────────────────────────────────

class Experiment(BaseModel):
    id: str
    name: str
    experiment_type: str
    description: str | None
    status: str
    ablation_variant: str | None
    precision: float | None
    recall: float | None
    f1_score: float | None
    false_positive_rate: float | None
    attack_success_rate: float | None
    results: dict[str, Any]
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


# ─── Dashboard Models ─────────────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    total_assessments: int
    active_runs: int
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    informational_findings: int
    attack_success_rate: float
    detection_precision: float | None
    detection_recall: float | None
    f1_score: float | None
    false_positive_rate: float | None
    pipeline_distribution: dict[str, int]
    severity_distribution: dict[str, int]
    recent_findings: list[dict]
    recent_runs: list[dict]
