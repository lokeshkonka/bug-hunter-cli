from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, timezone

class ReportFormat(str, Enum):
    markdown = "markdown"
    sarif = "sarif"
    json = "json"

class ReportSection(BaseModel):
    model_config = ConfigDict(frozen=True)
    title: str
    content: str

class Report(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    run_id: str
    format: ReportFormat
    path: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
