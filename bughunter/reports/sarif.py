import json
from pathlib import Path
from datetime import datetime, timezone
from bughunter.models.finding import Finding
from typing import List

class SarifExporter:
    @staticmethod
    def export(run_id: str, findings: List[Finding], output_dir: str) -> str:
        sarif_findings = []
        for finding in findings:
            sarif_findings.append({
                "ruleId": "BH-GENERIC" if not finding.category else finding.category,
                "level": "error" if finding.severity.value in ["high", "critical"] else "warning",
                "message": {
                    "text": finding.title
                },
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": finding.affected_component or "unknown"
                        },
                        "region": {
                            "startLine": 1,
                            "endLine": 1
                        }
                    }
                }],
                "properties": {
                    "risk_tier": finding.severity.value.upper(),
                    "vuln_score": finding.cvss_score * 10 if finding.cvss_score else 0, # Rough mapping for SARIF schema
                    "description": finding.description
                }
            })

        sarif_report = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "Bug Hunter CLI",
                        "version": "1.0.0",
                        "rules": []
                    }
                },
                "results": sarif_findings
            }]
        }
        
        output_path = Path(output_dir) / f"bug-report-{run_id}.sarif"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(sarif_report, f, indent=2)
            
        return str(output_path)
