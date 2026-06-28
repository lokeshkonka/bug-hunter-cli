import pytest
import asyncio
from pathlib import Path
from bughunter.scanners.static.semgrep import SemgrepScanner
from bughunter.scanners.static.semgrep_rules import SemgrepRuleManager

@pytest.mark.asyncio
async def test_semgrep_scanner_secrets(tmp_path):
    if not SemgrepRuleManager.check_semgrep_installed():
        pytest.skip("Semgrep is not installed")
        
    secret_file = tmp_path / "config.py"
    secret_file.write_text('api_key = "AKIAIOSFODNN7EXAMPLE"\n')
    
    scanner = SemgrepScanner("test-run-id")
    rules = ["p/secrets"]
    
    evidence_list = await scanner.scan(str(tmp_path), rules)
    
    assert len(evidence_list) > 0
    
    found_secret = False
    for ev in evidence_list:
        if ev.source_file.endswith("config.py"):
            found_secret = True
            assert "sk-1234567890abcdef" not in ev.metadata.get("redacted_lines", "")
            
    assert found_secret
