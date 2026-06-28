import httpx
import uuid
from typing import List, Optional
from bughunter.models.evidence import Evidence
from bughunter.core.safety.engine import SafetyPolicyEngine
from bughunter.models.policy import PolicyAction, PolicyDecisionEnum

class HeadersScanner:
    """Scans a target URL for missing security headers."""
    def __init__(self, run_id: str, safety_engine: SafetyPolicyEngine, test_plan_id: Optional[str] = None):
        self.run_id = run_id
        self.safety_engine = safety_engine
        self.test_plan_id = test_plan_id
        self.required_headers = [
            "Content-Security-Policy",
            "Strict-Transport-Security",
            "X-Frame-Options",
            "X-Content-Type-Options",
            "Permissions-Policy"
        ]

    async def scan(self, url: str) -> List[Evidence]:
        # Enforce safety check first
        decision = self.safety_engine.check(self.run_id, PolicyAction.network_request, url)
        if decision.decision == PolicyDecisionEnum.block:
            print(f"Network request to {url} blocked by safety policy: {decision.reason}")
            return []
            
        evidence_list = []
        try:
            # Note: verify=False is often necessary in pentesting tools, 
            # but ideally should be configurable in the scope.
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                response = await client.get(url)
                
            missing_headers = []
            for header in self.required_headers:
                if header.lower() not in [k.lower() for k in response.headers.keys()]:
                    missing_headers.append(header)
                    
            if missing_headers:
                observation = f"Missing security headers: {', '.join(missing_headers)}"
                evidence = Evidence(
                    id=str(uuid.uuid4()),
                    run_id=self.run_id,
                    test_plan_id=self.test_plan_id,
                    source_tool="headers_scanner",
                    observation=observation,
                    metadata={
                        "url": url,
                        "status_code": response.status_code,
                        "missing_headers": missing_headers
                    }
                )
                evidence_list.append(evidence)
                
        except Exception as e:
            print(f"Headers scanner failed for {url}: {e}")
            
        return evidence_list
