import os
from pathlib import Path
from bughunter.core.events.emitter import AgentEventEmitter
from bughunter.models.event import EventType
from bughunter.core.http.client import ScopedHttpClient
from bughunter.models.scope import Scope
from bughunter.providers.adapter import ProviderAdapter

class DynamicTestAgent:
    def __init__(self, run_id: str, emitter: AgentEventEmitter, http_client: ScopedHttpClient, db_path: str = ".bughunter/runs/bughunter.db"):
        self.run_id = run_id
        self.emitter = emitter
        self.http_client = http_client
        self.provider_adapter = ProviderAdapter(run_id, db_path)

    async def execute_test_plan(self, plan_path: Path, scope: Scope):
        await self.emitter.emit(self.run_id, EventType.tool_started, f"Executing {plan_path.name}")
        
        results_path = Path(".bughunter/runs") / self.run_id / "test-results.md"
        results_path.parent.mkdir(parents=True, exist_ok=True)
        
        plan_content = plan_path.read_text()
        
        if not scope.targets.urls:
            msg = f"Skipping dynamic test {plan_path.name}: No target URLs defined in scope."
            await self.emitter.emit(self.run_id, EventType.tool_completed, msg)
            with open(results_path, "a") as f:
                f.write(f"## Test {plan_path.name}\nStatus: skipped (No URLs in scope)\n")
            return

        for url in scope.targets.urls:
            try:
                await self.emitter.emit(self.run_id, EventType.tool_progress, f"Testing {url} for {plan_path.name}")
                
                # Use AI to execute dynamic validation based on the plan
                if scope.scan.mode.value == "lab-validation":
                    mode_instruction = "Since this is LAB-VALIDATION mode, you ARE AUTHORIZED to generate and validate aggressive exploit payloads, including SQLi drops, XSS alerts, or RCE proofs."
                elif scope.scan.mode.value == "passive":
                    mode_instruction = "Since this is PASSIVE mode, you may only analyze the URL conceptually. Do NOT suggest sending any HTTP requests."
                else:
                    mode_instruction = "Since you are restricted to SAFE-ACTIVE requests, draft ONLY safe, non-destructive HTTP requests to validate this vulnerability."

                prompt = f"""You are executing a dynamic security test against {url}.
Here is the test plan:
{plan_content}

{mode_instruction}
If this is a Static Analysis finding, write a proof-of-concept curl command or validation logic.

Respond with a JSON object containing:
- "status": "finding_confirmed", "passed", or "error"
- "details": The execution log or proof of concept.
- "score": A severity score out of 100 if confirmed.
"""
                response = await self.provider_adapter.llm.ainvoke(prompt)
                
                import json
                try:
                    # Strip markdown block if present
                    clean_resp = response.content.strip()
                    if clean_resp.startswith("```json"):
                        clean_resp = clean_resp.split("```json")[1].rsplit("```", 1)[0].strip()
                    elif clean_resp.startswith("```"):
                        clean_resp = clean_resp.split("```")[1].rsplit("```", 1)[0].strip()
                        
                    res = json.loads(clean_resp)
                    status = res.get("status", "error")
                    details = res.get("details", "")
                    score = float(res.get("score", 0.0))
                except Exception:
                    status = "error"
                    details = response.content
                    score = 0.0
                
                result = f"## Test {plan_path.name} on {url}\nStatus: {status}\nDetails: {details}\n"
                
                with open(results_path, "a") as f:
                    f.write(result)
                
                if status == "finding_confirmed":
                    await self.emitter.emit(self.run_id, EventType.finding_confirmed, f"Confirmed dynamic finding on {url}", {"severity": "HIGH" if score > 70 else "MEDIUM", "score": score})
                    
            except Exception as e:
                await self.emitter.emit(self.run_id, EventType.error, f"Error on {url}: {e}")
                
        await self.emitter.emit(self.run_id, EventType.tool_completed, f"Completed {plan_path.name}")
