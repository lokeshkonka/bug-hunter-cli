import os
from bughunter.core.events.emitter import AgentEventEmitter
from bughunter.models.event import EventType
from bughunter.models.finding import Finding

class FixAgent:
    def __init__(self, run_id: str, emitter: AgentEventEmitter):
        self.run_id = run_id
        self.emitter = emitter

    async def generate_fix(self, finding: Finding) -> dict:
        await self.emitter.emit(self.run_id, EventType.tool_started, f"Generating fix for {finding.id}")
        
        # Simulated LLM generation of fix
        complexity = "simple"
        penalty = -0.05
        
        if finding.severity.value == "critical":
            complexity = "moderate"
            penalty = -0.08
            
        fix_data = {
            "finding_id": finding.id,
            "description": "Implement parameterized queries or use the ORM's built-in escaping to prevent SQL injection.",
            "diff": "-\tresult = db.execute(f'SELECT * FROM users WHERE id = {user_id}')\n+\tresult = db.execute('SELECT * FROM users WHERE id = ?', [user_id])",
            "reference": "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
            "complexity": complexity,
            "penalty": penalty
        }
        
        await self.emitter.emit(self.run_id, EventType.tool_completed, f"Fix generated for {finding.id}")
        return fix_data
