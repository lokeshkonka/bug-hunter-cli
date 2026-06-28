from bughunter.core.secrets.redactor import SecretRedactor

def test_redact_openai_key():
    text = "Here is my key: sk-1234567890abcdef1234567890abcdef1234567890abcdef don't share it."
    redacted_text, metadata = SecretRedactor.redact(text)
    
    assert "sk-1234567890abcdef" not in redacted_text
    assert "REDACTED:sha256:" in redacted_text
    assert len(metadata) == 1
    assert metadata[0]["type"] == "openai_api_key"

def test_redact_generic_secret():
    text = "db_password = 'super_secret_password_123'"
    redacted_text, metadata = SecretRedactor.redact(text)
    
    assert "super_secret_password_123" not in redacted_text
    assert "db_password = 'REDACTED:sha256:" in redacted_text
    assert len(metadata) == 1
    assert metadata[0]["type"] == "generic_secret"
