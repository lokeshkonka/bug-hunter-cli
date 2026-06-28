import re

# Common secret patterns for Phase 1
SECRET_PATTERNS = {
    "openai_api_key": re.compile(r"sk-[a-zA-Z0-9]{48}"),
    "github_token": re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    "google_api_key": re.compile(r"AIza[0-9A-Za-z-_]{35}"),
    "slack_token": re.compile(r"xox[baprs]-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24}"),
    "aws_access_key": re.compile(r"(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"),
    "generic_secret": re.compile(r"(?i)(password|secret|token|api_key|apikey)[\s=:]+['\"]([a-zA-Z0-9\-_]{16,})['\"]")
}
