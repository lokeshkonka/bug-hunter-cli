import os
from pathlib import Path
from bughunter.core.events.emitter import AgentEventEmitter
from bughunter.models.event import EventType
from bughunter.storage.finding_store import FindingStore
from bughunter.providers.adapter import ProviderAdapter

class PlannerAgent:
    def __init__(self, run_id: str, emitter: AgentEventEmitter, db_path: str = ".bughunter/runs/bughunter.db"):
        self.run_id = run_id
        self.emitter = emitter
        self.db_path = db_path
        self.provider_adapter = ProviderAdapter(run_id, db_path)

    async def generate_test_plans(self, index_path: str):
        await self.emitter.emit(self.run_id, EventType.phase_started, "Test Planning")
        run_dir = Path(".bughunter/runs") / self.run_id
        testing_dir = run_dir / "testing"
        testing_dir.mkdir(parents=True, exist_ok=True)
        
        # Load findings from DB
        finding_store = FindingStore(self.db_path)
        findings = await finding_store.get_run_findings(self.run_id)
        
        if not findings:
            await self.emitter.emit(self.run_id, EventType.tool_progress, "No static findings found. Creating default health check test plan.")
            test_plan = """# Test T-001: Baseline Security Scan
**White-hat authorization**: This test is designed for authorized white-hat security validation of the scoped target only.

**Category**: config / headers
**Safety class**: safe-active

## Objective
Confirm whether the target exposes proper security headers.

## Method
1. Send benign baseline request to target URL
2. Parse response headers
3. Verify presence of security headers

## Expected Evidence
- Security headers in HTTP response

## Todo
- [ ] Send request
- [ ] Check headers
- [ ] Store evidence
"""
            file_path = testing_dir / "test1.md"
            with open(file_path, "w") as f:
                f.write(test_plan)
            return [file_path]

        test_plan_paths = []
        
        # Generate a test plan for each finding using AI
        for i, finding in enumerate(findings):
            await self.emitter.emit(self.run_id, EventType.tool_started, f"Generating test plan for finding: {finding.title}")
            
            prompt = f"""Generate a dynamic security test plan in Markdown format to verify this vulnerability:
            
Title: {finding.title}
Severity: {finding.severity.value}
Impact: {finding.impact}
Reproduction Steps: {finding.reproduction_steps}

The Markdown should include:
# Test T-{i+1:03d}: {finding.title}
**White-hat authorization**: This test is designed for authorized white-hat security validation of the scoped target only.
**Category**: {finding.category}

## Objective
...

## Method
...

## Expected Evidence
...
"""
            try:
                # Using basic completion for plan generation
                response = await self.provider_adapter.llm.ainvoke(prompt)
                test_plan = response.content
                
                file_path = testing_dir / f"test_{i+1}.md"
                with open(file_path, "w") as f:
                    f.write(test_plan)
                test_plan_paths.append(file_path)
                
                await self.emitter.emit(self.run_id, EventType.tool_completed, f"Generated test plan for {finding.title}")
            except Exception as e:
                await self.emitter.emit(self.run_id, EventType.error, f"Failed to generate test plan for {finding.title}: {e}")
                
        return test_plan_paths
