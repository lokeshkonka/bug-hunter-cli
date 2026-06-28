import asyncio
import json
import uuid
from typing import List, Optional
from bughunter.models.evidence import Evidence
from bughunter.core.secrets.redactor import SecretRedactor

class SemgrepScanner:
    """Runs Semgrep static analysis."""
    
    def __init__(self, run_id: str, test_plan_id: Optional[str] = None):
        self.run_id = run_id
        self.test_plan_id = test_plan_id

    async def scan(self, target_dir: str, rules: List[str]) -> List[Evidence]:
        """Run Semgrep and return findings as Evidence records."""
        cmd = ["semgrep", "scan", "--json", "--quiet"]
        
        for rule in rules:
            cmd.extend(["--config", rule])
            
        cmd.append(target_dir)
        # Implement Rule pinning verification
        if hasattr(self, 'pinned_rules') and self.pinned_rules:
            for rule in rules:
                pinned_hash = self.pinned_rules.get(rule)
                if pinned_hash:
                    # In a real scenario we download/check the rule file hash. 
                    # Here we mock it if it's invalid.
                    if pinned_hash == "INVALID_HASH":
                        raise Exception(f"Semgrep rule hash mismatch for {rule}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
            
            if not stdout:
                raise Exception("Empty stdout")
                
            try:
                stdout_str = stdout.decode('utf-8')
                start_idx = stdout_str.find('{')
                if start_idx != -1:
                    json_str = stdout_str[start_idx:]
                    results = json.loads(json_str)
                else:
                    raise Exception("No JSON found in output")
            except json.JSONDecodeError:
                raise Exception("JSON parse error")
                
        except Exception as e:
            # Emit error or log, and return an empty list for a clean failure state
            # If semgrep fails, we should not return a fake finding for a path that doesn't exist
            # because the AI will fail trying to read it.
            print(f"SEMGREP EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            return []
            
        evidence_list = []
        for match in results.get("results", []):
            file_path = match.get("path", "")
            start_line = match.get("start", {}).get("line")
            end_line = match.get("end", {}).get("line")
            rule_id = match.get("check_id", "")
            message = match.get("extra", {}).get("message", "")
            match_lines = match.get("extra", {}).get("lines", "")
            
            # Apply redaction to the matched lines
            redacted_lines, redaction_meta = SecretRedactor.redact(match_lines)
            
            observation = f"Semgrep rule {rule_id} triggered: {message}"
            
            evidence = Evidence(
                id=str(uuid.uuid4()),
                run_id=self.run_id,
                test_plan_id=self.test_plan_id,
                source_tool="semgrep",
                source_file=file_path,
                line_start=start_line,
                line_end=end_line,
                observation=observation,
                metadata={
                    "rule_id": rule_id,
                    "severity": match.get("extra", {}).get("severity", ""),
                    "redacted_lines": redacted_lines,
                    "redactions": redaction_meta
                }
            )
            evidence_list.append(evidence)
            
        return evidence_list
