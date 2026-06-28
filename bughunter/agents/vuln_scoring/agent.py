import os
from pathlib import Path
from bughunter.core.events.emitter import AgentEventEmitter
from bughunter.models.event import EventType
from bughunter.models.finding import Finding

class VulnScoringAgent:
    def __init__(self, run_id: str, emitter: AgentEventEmitter):
        self.run_id = run_id
        self.emitter = emitter

    async def score_finding(self, finding: Finding, evidence_items: list) -> float:
        await self.emitter.emit(self.run_id, EventType.tool_started, f"Scoring finding {finding.id}")
        
        # 1. Evidence Weight
        evidence_weight = min(5.0, len(evidence_items) * 2.0)
        
        # 2. CVSS (Mocked for now based on severity)
        cvss = 5.0
        if finding.severity.value == "critical":
            cvss = 9.5
        elif finding.severity.value == "high":
            cvss = 7.5
        elif finding.severity.value == "medium":
            cvss = 5.5
        else:
            cvss = 3.0
            
        # 3. AI Confidence
        ai_prob = 0.80 if evidence_weight > 0 else 0.40
        
        # 4. Exploit Factor
        exploit_factor = 0.50
        
        # 5. Remediation Penalty
        remed_penalty = -0.05
        
        # Compute VulnScore
        raw = (cvss * 0.35) + (ai_prob * 10 * 0.25) + (evidence_weight * 2 * 0.20) + (exploit_factor * 10 * 0.12)
        adjusted = raw + (remed_penalty * raw)
        normalized = (adjusted / 9.2) * 100
        vuln_score = max(0.0, min(100.0, normalized))
        
        tier = "INFO"
        if vuln_score >= 85: tier = "CRITICAL"
        elif vuln_score >= 65: tier = "HIGH"
        elif vuln_score >= 40: tier = "MEDIUM"
        elif vuln_score >= 15: tier = "LOW"
        
        await self.emitter.emit(
            self.run_id, 
            EventType.finding_confirmed, 
            f"Scored {finding.title} as {tier} ({vuln_score:.1f})", 
            {"severity": tier, "score": vuln_score, "finding_id": finding.id}
        )
        
        return vuln_score
