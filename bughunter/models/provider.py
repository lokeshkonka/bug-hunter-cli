from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime, timezone

class ProviderConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    provider_name: str
    model_name: str
    api_key: str

class UsageRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    run_id: str
    agent: str
    test_id: Optional[str] = None
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    cached: bool = False
    called_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CvssVector(BaseModel):
    model_config = ConfigDict(frozen=True)
    vector_string: str
