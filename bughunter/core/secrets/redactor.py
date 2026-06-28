import hashlib
from typing import Tuple, Dict, Any, List
from bughunter.core.secrets.patterns import SECRET_PATTERNS

class SecretRedactor:
    """Redacts secrets from text using predefined patterns."""

    @staticmethod
    def redact(text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Redacts secrets in text and returns the redacted text along with metadata
        about what was redacted.
        """
        redacted_text = text
        metadata = []

        for secret_type, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(redacted_text):
                secret_value = match.group(0)
                
                # For generic secrets, we want to only redact the value part, not the key.
                if secret_type == "generic_secret":
                    secret_value = match.group(2)
                
                # Create a hash of the secret
                secret_hash = hashlib.sha256(secret_value.encode()).hexdigest()
                replacement = f"REDACTED:sha256:{secret_hash}"
                
                # Replace it in the text
                redacted_text = redacted_text.replace(secret_value, replacement)
                
                metadata.append({
                    "type": secret_type,
                    "hash": secret_hash
                })

        return redacted_text, metadata
