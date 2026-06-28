from typing import List
from pathlib import Path
from datetime import datetime, timezone
from bughunter.models.finding import Finding
from bughunter.models.evidence import Evidence

class MarkdownExporter:
    @staticmethod
    def export(run_id: str, findings: List[Finding], evidence_list: List[Evidence], output_dir: str = ".") -> str:
        """Renders findings to a Markdown report and returns the file path."""
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_path = path / f"bug-report-{run_id[:8]}-{timestamp}.md"
        
        lines = [
            f"# 🛡️ Bug Hunter CLI — Security Report",
            f"**Run ID:** `{run_id}`",
            f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "## 📊 Scan Summary",
            f"**Total Findings:** {len(findings)}",
            ""
        ]
        
        # Sort findings by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_findings = sorted(findings, key=lambda f: severity_order.get(f.severity.value.lower(), 4))
        
        # Summary Table
        if sorted_findings:
            lines.extend([
                "| Severity | Finding Title | Category | Component |",
                "|---|---|---|---|"
            ])
            for f in sorted_findings:
                sev_icon = {"critical": "🚨", "high": "🔴", "medium": "🟠", "low": "🟡"}.get(f.severity.value.lower(), "⚪")
                lines.append(f"| {sev_icon} **{f.severity.value.upper()}** | {f.title} | {f.category} | `{f.affected_component}` |")
            lines.extend(["", "---", ""])

        lines.append("## 🔎 Detailed Findings")
        
        for idx, finding in enumerate(sorted_findings, 1):
            sev_icon = {"critical": "🚨", "high": "🔴", "medium": "🟠", "low": "🟡"}.get(finding.severity.value.lower(), "⚪")
            lines.extend([
                f"### {idx}. {sev_icon} [{finding.severity.value.upper()}] {finding.title}",
                "",
                f"> **Category:** {finding.category}  ",
                f"> **Component:** `{finding.affected_component}`  ",
                "",
                "#### 💥 Impact",
                finding.impact,
                "",
                "#### 📝 Reproduction Steps",
                finding.reproduction_steps,
                "",
                "#### 🔍 Evidence"
            ])
            
            finding_evidence = [e for e in evidence_list if e.id in finding.evidence_ids]
            if not finding_evidence:
                lines.append("*No automated evidence attached.*")
            else:
                for ev in finding_evidence:
                    lines.append(f"- **Tool:** `{ev.source_tool}` in `{ev.source_file}`")
                    lines.append(f"  - **Observation:** {ev.observation}")
                    
                    redacted_lines = ev.metadata.get("redacted_lines")
                    if redacted_lines:
                        lines.extend([
                            "",
                            "  ```text",
                            f"  {redacted_lines}",
                            "  ```",
                            ""
                        ])
            
            lines.extend([
                "",
                "#### 🛠️ Recommendation",
                finding.recommendation,
                "",
                "---",
                ""
            ])
            
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            
        return str(report_path)
