import json
from pathlib import Path
from datetime import datetime, timezone
from bughunter.models.finding import Finding
from typing import List

class JsonExporter:
    @staticmethod
    def export(run_id: str, findings: List[Finding], output_dir: str) -> str:
        json_findings = []
        for finding in findings:
            json_findings.append({
                "id": finding.id,
                "title": finding.title,
                "severity": finding.severity.value.upper(),
                "category": finding.category,
                "affected": finding.affected_component,
                "description": finding.description,
            })

        json_report = {
            "run_id": run_id,
            "scan_date": datetime.now(timezone.utc).isoformat(),
            "findings": json_findings
        }
        
        output_path = Path(output_dir) / f"bug-report-{run_id}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(json_report, f, indent=2)
            
        return str(output_path)
