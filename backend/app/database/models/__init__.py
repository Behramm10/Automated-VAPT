"""
Database Models Package — registers all ORM models for SQLAlchemy.

Import this package to ensure all models are registered with the metadata.
"""
from app.database.models.target_model import (
    TargetModel,
    TargetCapabilityModel,
    AuthorizationRecordModel,
)
from app.database.models.run_model import (
    RunModel,
    TestPlanModel,
    TestCaseModel,
    SessionModel,
)
from app.database.models.payload_model import (
    PayloadModel,
    ArtifactModel,
)
from app.database.models.telemetry_model import (
    TelemetryEventModel,
    InstructionSpanModel,
)
from app.database.models.finding_model import (
    FindingModel,
    EvaluationModel,
    EvaluationSignalModel,
    EvidenceBundleModel,
)
from app.database.models.attack_graph_model import (
    AttackGraphModel,
    AttackGraphNodeModel,
    AttackGraphEdgeModel,
)
from app.database.models.report_model import (
    ReportModel,
    ExperimentModel,
    BenchmarkCaseModel,
)

__all__ = [
    "TargetModel",
    "TargetCapabilityModel",
    "AuthorizationRecordModel",
    "RunModel",
    "TestPlanModel",
    "TestCaseModel",
    "SessionModel",
    "PayloadModel",
    "ArtifactModel",
    "TelemetryEventModel",
    "InstructionSpanModel",
    "FindingModel",
    "EvaluationModel",
    "EvaluationSignalModel",
    "EvidenceBundleModel",
    "AttackGraphModel",
    "AttackGraphNodeModel",
    "AttackGraphEdgeModel",
    "ReportModel",
    "ExperimentModel",
    "BenchmarkCaseModel",
]
