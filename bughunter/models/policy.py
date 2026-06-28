from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime, timezone

class PolicyAction(str, Enum):
    network_request = "network_request"
    file_read = "file_read"
    tool_execution = "tool_execution"

class PolicyDecisionEnum(str, Enum):
    allow = "allow"
    allow_with_limits = "allow_with_limits"
    downgrade = "downgrade"
    block = "block"

class PolicyDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    run_id: str
    action: PolicyAction
    target: str
    decision: PolicyDecisionEnum
    reason: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class PolicyViolation(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    run_id: str
    action: PolicyAction
    target: str
    reason: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
