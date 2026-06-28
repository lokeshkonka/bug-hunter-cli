from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Optional

class FileRelevance(BaseModel):
    model_config = ConfigDict(frozen=True)
    file_path: str
    score: float
    tags: List[str]
    reasons: List[str]

class RepositoryManifest(BaseModel):
    model_config = ConfigDict(frozen=True)
    project_root: str
    languages: List[str]
    frameworks: List[str]
    dependency_files: List[str]
    route_files: List[str]
    middleware_files: List[str]
    config_files: List[str]
    auth_files: List[str]
    db_files: List[str]
    upload_files: List[str]
    job_files: List[str]
    test_files: List[str]
    excluded_files: List[str]
    scored_files: List[FileRelevance]
