from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, timezone

class SafetyClass(str, Enum):
    passive = "passive"
    safe_active = "safe-active"
    lab_validation = "lab-validation"
    blocked = "blocked"

class TestCategory(str, Enum):
    static_analysis = "static_analysis"
    dynamic_scan = "dynamic_scan"
    secret_scan = "secret_scan"
    dependency_audit = "dependency_audit"

class TestPlan(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    run_id: str
    title: str
    category: TestCategory
    safety_class: SafetyClass
    target: str
    plan_path: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
