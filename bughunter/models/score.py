from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime, timezone

class RiskTier(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class VulnScore(BaseModel):
    model_config = ConfigDict(frozen=True)
    score: float
    tier: RiskTier

class ScoreComponents(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    finding_id: str
    run_id: str
    cvss_score: Optional[float] = None
    confidence_score: Optional[float] = None
    exploitability_score: Optional[float] = None
    remediation_score: Optional[float] = None
    evidence_weight: Optional[float] = None
    composite_score: Optional[float] = None
    risk_tier: Optional[RiskTier] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
