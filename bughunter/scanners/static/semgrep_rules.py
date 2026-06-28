import subprocess
from typing import List

class SemgrepRuleManager:
    """Manages Semgrep rule packs for different phases of the pipeline."""
    
    @staticmethod
    def get_phase1_rules() -> List[str]:
        """Returns the minimal set of rules required for Phase 1 testing."""
        return [
            "p/secrets", 
        ]

    @staticmethod
    def get_phase2_rules() -> List[str]:
        """Returns the full set of security rules for Phase 2 deep scanning."""
        return [
            "p/security-audit", "p/owasp-top-ten", "p/secrets",
            "p/supply-chain", "p/python", "p/javascript",
            "p/typescript", "p/java", "p/ruby", "p/golang", "p/php",
            "p/django", "p/flask", "p/expressjs", "p/react"
        ]

    @staticmethod
    def check_semgrep_installed() -> bool:
        """Check if semgrep is available on the system."""
        try:
            subprocess.run(
                ["semgrep", "--version"], 
                capture_output=True, 
                check=True, 
                text=True
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
