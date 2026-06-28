import pytest
from bughunter.core.safety.scope_validator import ScopeValidator
from bughunter.models.scope import Scope, ScanMode
import yaml

def test_load_and_validate_success(tmp_path):
    scope_content = """
project:
  name: test-app
  repo_path: .
targets:
  urls:
    - http://localhost:8000
scan:
  mode: safe-active
"""
    file_path = tmp_path / "scope.yml"
    file_path.write_text(scope_content)
    
    scope = ScopeValidator.load_and_validate(str(file_path))
    assert scope.project.name == "test-app"
    assert "http://localhost:8000" in scope.targets.urls
    assert scope.scan.mode == ScanMode.safe_active

def test_validate_semantics_wildcard_url(tmp_path):
    scope_content = """
project:
  name: test-app
targets:
  urls:
    - http://*.example.com
"""
    file_path = tmp_path / "scope.yml"
    file_path.write_text(scope_content)
    
    with pytest.raises(ValueError, match="Wildcards are not allowed in URLs"):
        ScopeValidator.load_and_validate(str(file_path))

def test_validate_semantics_lab_validation(tmp_path):
    scope_content = """
project:
  name: test-app
targets:
  urls:
    - http://localhost:8000
scan:
  mode: lab-validation
safety:
  allow_lab_validation: false
"""
    file_path = tmp_path / "scope.yml"
    file_path.write_text(scope_content)
    
    with pytest.raises(ValueError, match="requires safety.allow_lab_validation = true"):
        ScopeValidator.load_and_validate(str(file_path))
