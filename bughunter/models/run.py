from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime, timezone

class RunStatus(str, Enum):
    created = "created"
    scanning = "scanning"
    completed = "completed"
    failed = "failed"

class Run(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    status: RunStatus = RunStatus.created
    scope_path: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    token_budget: int
    cost_budget_usd: float

class RunSummary(BaseModel):
    model_config = ConfigDict(frozen=True)
    run_id: str
    status: RunStatus
    total_findings: int
    critical_findings: int
    high_findings: int
