import os
from pathlib import Path
from typing import List, Dict, Tuple
from bughunter.models.manifest import RepositoryManifest, FileRelevance

DEFAULT_IGNORE_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build", ".next", ".cache", ".tox", "coverage", "htmlcov"}
DEFAULT_IGNORE_EXTS = {".pyc", ".min.js", ".map", ".lock", ".jpg", ".png", ".gif", ".mp4", ".woff", ".ttf", ".eot", ".sqlite3", ".db"}

class ManifestBuilder:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        
    def build(self) -> RepositoryManifest:
        languages = set()
        frameworks = set()
        
        manifest_data = {
            "dependency_files": [],
            "route_files": [],
            "middleware_files": [],
            "config_files": [],
            "auth_files": [],
            "db_files": [],
            "upload_files": [],
            "job_files": [],
            "test_files": [],
            "excluded_files": [],
            "scored_files": []
        }
        
        for dirpath, dirnames, filenames in os.walk(self.project_root):
            # Ignore directories
            dirnames[:] = [d for d in dirnames if d not in DEFAULT_IGNORE_DIRS]
            
            for file in filenames:
                file_path = Path(dirpath) / file
                rel_path = file_path.relative_to(self.project_root).as_posix()
                
                # Skip ignore exts and hidden files (except .env)
                if file_path.suffix in DEFAULT_IGNORE_EXTS or (file.startswith(".") and file != ".env"):
                    manifest_data["excluded_files"].append(rel_path)
                    continue
                    
                # Detect language
                if file.endswith(".py"): languages.add("python")
                elif file.endswith(".js") or file.endswith(".ts"): languages.add("javascript")
                elif file.endswith(".go"): languages.add("go")
                elif file.endswith(".java"): languages.add("java")
                elif file.endswith(".rb"): languages.add("ruby")
                elif file.endswith(".php"): languages.add("php")
                
                # Detect frameworks/dependencies
                if file in ["requirements.txt", "Pipfile", "pyproject.toml"]:
                    manifest_data["dependency_files"].append(rel_path)
                    if file == "requirements.txt": frameworks.add("python-pip")
                elif file == "package.json":
                    manifest_data["dependency_files"].append(rel_path)
                    frameworks.add("nodejs")
                elif file == "pom.xml":
                    frameworks.add("java-maven")
                elif file == "Gemfile":
                    frameworks.add("ruby-bundler")
                    
                # Score file and categorize
                score, tags, reasons = self._score_file(rel_path)
                
                if score >= 0.3:
                    manifest_data["scored_files"].append(FileRelevance(
                        file_path=rel_path, score=score, tags=tags, reasons=reasons
                    ))
                    
                    # Categorize based on tags/name
                    name_lower = file.lower()
                    if "test" in name_lower or "tests/" in rel_path: manifest_data["test_files"].append(rel_path)
                    if any(t in tags for t in ["auth"]): manifest_data["auth_files"].append(rel_path)
                    if any(t in tags for t in ["db"]): manifest_data["db_files"].append(rel_path)
                    if any(t in tags for t in ["config"]): manifest_data["config_files"].append(rel_path)
                    if any(t in tags for t in ["route"]): manifest_data["route_files"].append(rel_path)
                else:
                    manifest_data["excluded_files"].append(rel_path)
                    
        return RepositoryManifest(
            project_root=str(self.project_root),
            languages=list(languages),
            frameworks=list(frameworks),
            **manifest_data
        )

    def _score_file(self, rel_path: str) -> Tuple[float, List[str], List[str]]:
        score = 0.0
        tags = set()
        reasons = []
        name_lower = rel_path.lower()
        
        # Factor 1: Auth
        if any(kw in name_lower for kw in ["login", "auth", "session", "token", "user", "admin", "passport"]):
            score += 0.30
            tags.add("auth")
            reasons.append("Contains auth-related keywords")
            
        # Factor 2: Routes
        if any(kw in name_lower for kw in ["route", "view", "controller", "handler", "endpoint", "api"]):
            score += 0.25
            tags.add("route")
            reasons.append("Contains routing keywords")
            
        # Factor 3: Configs
        if any(kw in name_lower for kw in ["config", "settings", "env", "secret", "key"]):
            score += 0.25
            tags.add("config")
            reasons.append("Contains config/secret keywords")
            
        # Factor 4: Payments
        if any(kw in name_lower for kw in ["payment", "billing", "order", "checkout"]):
            score += 0.20
            tags.add("business-logic")
            reasons.append("Contains payment keywords")
            
        # Factor: Tests
        if "test" in name_lower or "/tests/" in name_lower or "spec" in name_lower:
            score -= 0.10
            reasons.append("Test file penalty")
            
        # Read a bit of content for simple static matching (sql, file upload)
        try:
            with open(self.project_root / rel_path, "r", encoding="utf-8") as f:
                content = f.read(4096).lower() # Read first 4KB
                if "select " in content or "insert " in content or "update " in content or "delete " in content:
                    score += 0.15
                    tags.add("db")
                    reasons.append("Contains SQL-like keywords in content")
                if "upload" in content or "file.save" in content or "multipart" in content:
                    score += 0.15
                    tags.add("upload")
                    reasons.append("Contains upload keywords in content")
        except Exception:
            pass
            
        return round(score, 2), list(tags), reasons
