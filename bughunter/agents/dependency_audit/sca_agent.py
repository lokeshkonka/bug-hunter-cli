import asyncio
import json
import uuid
import os
from pathlib import Path
from bughunter.core.events.emitter import AgentEventEmitter
from bughunter.models.event import EventType
from bughunter.storage.finding_store import FindingStore
from bughunter.models.finding import Finding, Severity, Confidence

class DependencyAuditAgent:
    """Agent that runs SCA (Software Composition Analysis) to find CVEs in dependencies."""
    
    def __init__(self, run_id: str, emitter: AgentEventEmitter, db_path: str):
        self.run_id = run_id
        self.emitter = emitter
        self.db_path = db_path
        self.finding_store = FindingStore(db_path)

    async def run_audit(self, target_dir: str):
        await self.emitter.emit(self.run_id, EventType.phase_started, "Dependency Audit Phase")
        
        target_path = Path(target_dir)
        package_json = target_path / "package.json"
        
        if package_json.exists():
            await self.emitter.emit(self.run_id, EventType.tool_started, "Running npm audit to check for CVEs...")
            await self._run_npm_audit(target_dir)
        else:
            await self.emitter.emit(self.run_id, EventType.tool_progress, "No package.json found. Skipping npm audit.")
            
        await self.emitter.emit(self.run_id, EventType.tool_completed, "Dependency Audit complete.")

    async def _run_npm_audit(self, target_dir: str):
        try:
            process = await asyncio.create_subprocess_exec(
                "npm", "audit", "--json",
                cwd=target_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=60)
            
            if not stdout:
                return
                
            results = json.loads(stdout.decode('utf-8'))
            
            # npm audit returns vulnerabilities in a dict under "vulnerabilities"
            vulns = results.get("vulnerabilities", {})
            for pkg_name, details in vulns.items():
                if details.get("severity") in ["high", "critical"]:
                    await self._record_cve_finding(pkg_name, details)
                    
        except Exception as e:
            await self.emitter.emit(self.run_id, EventType.error, f"Failed to run npm audit: {str(e)}")
            
    async def _record_cve_finding(self, pkg_name: str, details: dict):
        severity_str = details.get("severity", "medium").lower()
        sev_map = {
            "critical": Severity.critical,
            "high": Severity.high,
            "moderate": Severity.medium,
            "low": Severity.low
        }
        severity = sev_map.get(severity_str, Severity.medium)
        
        via = details.get("via", [])
        title = f"Vulnerable Dependency: {pkg_name}"
        if isinstance(via, list) and len(via) > 0 and isinstance(via[0], dict):
            title = via[0].get("title", title)
            
        finding = Finding(
            id=str(uuid.uuid4()),
            run_id=self.run_id,
            title=f"[CVE] {title}",
            severity=severity,
            confidence=Confidence.certain,
            category="Software Composition Analysis (SCA)",
            affected_component=f"package.json ({pkg_name})",
            impact=f"The package '{pkg_name}' contains known vulnerabilities. This can lead to system compromise if the vulnerable code path is reachable.",
            reproduction_steps=f"Run `npm audit` to view the full dependency chain for {pkg_name}.",
            recommendation=f"Run `npm audit fix` or manually update {pkg_name} to a secure version in package.json."
        )
        
        await self.finding_store.insert_finding(finding)
        await self.emitter.emit(
            self.run_id, 
            EventType.finding_confirmed, 
            f"Found CVE in {pkg_name}", 
            {"severity": finding.severity.value, "finding_id": finding.id}
        )
