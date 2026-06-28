from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from typing import List
from datetime import datetime, timezone

class TestStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"

class TestResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    run_id: str
    test_plan_id: str
    status: TestStatus
    tools_run: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    finding_ids: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
