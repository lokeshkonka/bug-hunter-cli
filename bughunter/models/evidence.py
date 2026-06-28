from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any, Optional
from datetime import datetime, timezone

class EvidenceType(str, Enum):
    code_snippet = "code_snippet"
    http_request_response = "http_request_response"
    tool_output = "tool_output"

class EvidenceWeight(BaseModel):
    model_config = ConfigDict(frozen=True)
    weight: float

class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    run_id: str
    test_plan_id: Optional[str] = None
    source_tool: str
    source_file: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    observation: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
