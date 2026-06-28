from typing import List, Dict, Any, Optional
from bughunter.storage.evidence_store import EvidenceStore

class EvidenceAgent:
    def __init__(self, run_id: str, db_path: str):
        self.run_id = run_id
        self.evidence_store = EvidenceStore(db_path)
        
    async def process_raw_evidence(
        self,
        test_plan_id: Optional[str],
        source_tool: str,
        source_file: str,
        line_start: int,
        line_end: int,
        observation: str,
        metadata: str
    ) -> str:
        # 1. Redact secrets (mocked for now)
        redacted_observation = self._redact_secrets(observation)
        
        # 2. Check for deduplication
        existing = await self.evidence_store.get_evidence_by_file(self.run_id, source_file)
        
        # Simple deduplication: if exact same observation for same tool on same line range exists, ignore.
        for ev in existing:
            if (ev["source_tool"] == source_tool and 
                ev["line_start"] == line_start and 
                ev["line_end"] == line_end and 
                ev["observation"] == redacted_observation):
                return ev["id"] # Return existing ID
                
        # 3. Insert new evidence
        evidence_id = await self.evidence_store.insert_evidence(
            run_id=self.run_id,
            test_plan_id=test_plan_id,
            source_tool=source_tool,
            source_file=source_file,
            line_start=line_start,
            line_end=line_end,
            observation=redacted_observation,
            metadata=metadata
        )
        return evidence_id
        
    def _redact_secrets(self, text: str) -> str:
        # Stub for SecretRedactor
        # In a real implementation this would use regex and entropy to mask secrets
        import re
        # Mask obvious passwords/keys
        text = re.sub(r'(api_key|password|secret)(\s*[:=]\s*)["\'][^"\']+["\']', r'\1\2"***REDACTED***"', text, flags=re.IGNORECASE)
        return text
