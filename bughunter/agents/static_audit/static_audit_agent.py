from typing import List, Optional
import json
from pydantic import BaseModel, Field
from bughunter.models.run import Run
from bughunter.core.events.emitter import AgentEventEmitter
from bughunter.models.event import EventType
from bughunter.agents.context_manager.context_manager_agent import ContextManagerAgent
from bughunter.providers.adapter import ProviderAdapter
from bughunter.scanners.static.semgrep import SemgrepScanner
from bughunter.scanners.static.semgrep_rules import SemgrepRuleManager
from bughunter.agents.evidence.evidence_agent import EvidenceAgent

class FindingResult(BaseModel):
    is_vulnerable: bool = Field(description="Whether the provided snippet contains a vulnerability.")
    vulnerability_type: str = Field(default="", description="The type of vulnerability (e.g. SQL Injection). Empty string if false positive.")
    severity: str = Field(default="", description="Severity: Low, Medium, High, Critical. Empty string if false positive.")
    explanation: str = Field(description="Explanation of the vulnerability.")

class StaticAuditAgent:
    def __init__(self, run: Run, db_path: str, emitter: AgentEventEmitter, scope=None):
        self.run = run
        self.db_path = db_path
        self.emitter = emitter
        self.scope = scope
        self.context_manager = ContextManagerAgent(run, db_path, emitter)
        self.provider_adapter = ProviderAdapter(run.id, db_path)
        self.evidence_agent = EvidenceAgent(run.id, db_path)
        
    async def run_audit(self, target_dir: str):
        await self.emitter.emit(self.run.id, EventType.phase_started, "Static Audit Phase")
        
        # 1. Run Semgrep
        if SemgrepRuleManager.check_semgrep_installed():
            await self.emitter.emit(self.run.id, EventType.tool_started, "Running Semgrep scans")
            rules = SemgrepRuleManager.get_phase2_rules()
            scanner = SemgrepScanner(self.run.id)
            
            if self.scope and hasattr(self.scope.scan, 'semgrep'):
                pinned = {}
                for r in self.scope.scan.semgrep.rules:
                    if r.sha256:
                        pinned[r.id] = r.sha256
                scanner.pinned_rules = pinned
                
            evidences = await scanner.scan(target_dir, rules)
            
            await self.emitter.emit(self.run.id, EventType.tool_completed, f"Semgrep completed. Found {len(evidences)} potential issues.")
            
            # Process semgrep evidence
            for ev in evidences:
                await self.evidence_agent.process_raw_evidence(
                    test_plan_id=None,
                    source_tool="semgrep",
                    source_file=ev.source_file,
                    line_start=ev.line_start,
                    line_end=ev.line_end,
                    observation=ev.observation,
                    metadata=json.dumps(ev.metadata)
                )
                
                # Use ContextManager and AI to evaluate this snippet
                await self._evaluate_snippet_with_ai(ev.source_file, ev.line_start, ev.line_end, ev.observation)
        else:
            await self.emitter.emit(self.run.id, EventType.error, "Semgrep is not installed. Skipping Semgrep scans.")
            
    async def _evaluate_snippet_with_ai(self, file_path: str, line_start: int, line_end: int, context_obs: str):
        # Fetch actual code snippet using ContextManager logic (simplified here)
        snippet = f"File: {file_path} (Lines {line_start}-{line_end})\nObservation: {context_obs}"
        
        # Read the file
        try:
            await self.emitter.emit(self.run.id, EventType.tool_started, f"Agent reading file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                start = max(0, line_start - 5)
                end = min(len(lines), line_end + 5)
                code_content = "".join(lines[start:end])
                snippet += f"\nCode:\n{code_content}"
        except Exception:
            snippet += "\n[Error reading file]"
            
        # Check budget
        estimated_tokens = self.context_manager.estimate_tokens(snippet) + 500
        budget_ok = await self.context_manager.check_budget("static_audit", estimated_tokens)
        
        if not budget_ok:
            await self.emitter.emit(self.run.id, EventType.error, "Token budget exhausted. Skipping AI evaluation.")
            return
            
        system_prompt = (
            "You are a strict security auditor. Evaluate the provided code snippet and observation "
            "for actual security vulnerabilities. Ignore false positives."
        )
        
        await self.emitter.emit(self.run.id, EventType.tool_started, f"AI evaluating snippet in {file_path}")
        
        try:
            result: FindingResult = await self.provider_adapter.send_with_guard(
                agent="static_audit",
                system_prompt=system_prompt,
                untrusted_content=snippet,
                response_schema=FindingResult
            )
            
            if result.is_vulnerable:
                await self.emitter.emit(self.run.id, EventType.tool_completed, f"Vulnerability confirmed: {result.vulnerability_type} ({result.severity}) in {file_path}")
                
                from bughunter.storage.finding_store import FindingStore
                from bughunter.models.finding import Finding, Severity, Confidence
                import uuid
                
                finding = Finding(
                    id=str(uuid.uuid4()),
                    run_id=self.run.id,
                    title=f"{result.vulnerability_type} in {file_path}",
                    severity=Severity(result.severity.lower()) if result.severity and result.severity.lower() in [s.value for s in Severity] else Severity.medium,
                    confidence=Confidence.certain,
                    category="Static Audit",
                    affected_component=file_path,
                    evidence_ids=[], # Should link evidence here
                    impact=result.explanation,
                    reproduction_steps=f"Review file {file_path} at lines {line_start}-{line_end}",
                    recommendation="Review the code and implement appropriate security controls.",
                    retest_steps="Verify code changes resolve the issue without breaking functionality."
                )
                
                finding_store = FindingStore(self.db_path)
                await finding_store.insert_finding(finding)
                
                await self.emitter.emit(
                    self.run.id, 
                    EventType.finding_confirmed, 
                    f"Found {result.vulnerability_type} in {file_path}", 
                    {"severity": finding.severity.value, "finding_id": finding.id}
                )
            else:
                await self.emitter.emit(self.run.id, EventType.tool_completed, f"Snippet evaluated as safe: {file_path}")
                
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            await self.emitter.emit(self.run.id, EventType.error, f"AI evaluation failed: {str(e)}\n{tb_str}")
