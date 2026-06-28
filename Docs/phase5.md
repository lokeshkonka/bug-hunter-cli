# Phase 5: CI Integration, Exports, and Robustness

## Goal

Make Bug Hunter CLI production-ready for team and CI/CD use. Phase 5 adds:

- SARIF 2.1.0 export for GitHub Code Scanning and other SAST platforms
- JSON export for machine-readable CI consumption
- GitHub Actions integration example
- GitHub issue export command
- Plugin-style test packs (org-specific custom rules)
- Complete fixture app suite with documented vulnerability map
- Prompt injection test suite
- Cost control CI enforcement
- Lockfile-pinned Semgrep rule versions

---

## Deliverables

- SARIF 2.1.0 exporter (valid schema).
- JSON exporter (machine-readable findings).
- `bughunter export --format sarif/json` command.
- GitHub Actions workflow example (`bughunter-scan.yml`).
- GitHub issue export (`bughunter github-issue --run <id> --finding <id>`).
- Plugin test pack loader.
- Complete vulnerable Flask fixture app (Python) with documented vuln map.
- Complete vulnerable Express fixture app (Node.js) with documented vuln map.
- Prompt injection test suite (tests that PromptGuardAgent blocks all patterns).
- CI exit code enforcement (fail on CRITICAL, fail on cost threshold).
- Semgrep rule version pinning in `bughunter-scope.yml`.

---

## SARIF Export

SARIF (Static Analysis Results Interchange Format) 2.1.0 is the standard format for security findings in GitHub Code Scanning, VS Code, and many SAST platforms.

### SARIF Output Structure

```json
{
  "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
  "version": "2.1.0",
  "runs": [{
    "tool": {
      "driver": {
        "name": "Bug Hunter CLI",
        "version": "1.0.0",
        "rules": [
          {
            "id": "BH-001",
            "name": "SQLInjection",
            "shortDescription": { "text": "SQL Injection" },
            "properties": {
              "tags": ["security", "sql", "owasp-a03"],
              "security-severity": "9.8"
            }
          }
        ]
      }
    },
    "results": [
      {
        "ruleId": "BH-001",
        "level": "error",
        "message": { "text": "SQL Injection via format string in login handler" },
        "locations": [{
          "physicalLocation": {
            "artifactLocation": { "uri": "auth/views.py" },
            "region": { "startLine": 142, "endLine": 142 }
          }
        }],
        "properties": {
          "vuln_score": 94,
          "risk_tier": "CRITICAL",
          "ai_confidence": 0.91,
          "cvss_vector": "AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N"
        }
      }
    ]
  }]
}
```

### SARIF Validation

- Output must pass SARIF schema validation before being written.
- Use `sarif-tools` or `jsonschema` library for validation.
- Invalid SARIF is a test failure.

---

## JSON Export

Machine-readable JSON export for custom CI pipelines, dashboards, and integrations.

```json
{
  "run_id": "abc123",
  "scan_date": "2026-06-25T14:32:00Z",
  "scope": "http://localhost:3000",
  "scan_mode": "safe-active",
  "summary": {
    "total_findings": 7,
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 0,
    "informational": 1,
    "top_vuln_score": 94,
    "mean_vuln_score": 61.4,
    "tokens_used": 12440,
    "estimated_cost_usd": 0.04
  },
  "findings": [
    {
      "id": "f001",
      "title": "SQL Injection",
      "vuln_score": 94,
      "risk_tier": "CRITICAL",
      "ai_confidence": 0.91,
      "category": "injection/sql",
      "affected": "auth/views.py:142",
      "status": "confirmed",
      "semgrep_rules": ["python.django.security.audit.raw-query"],
      "cvss_vector": "AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N",
      "evidence_count": 3
    }
  ]
}
```

---

## CI Integration

### CI Mode

Bug Hunter CLI detects non-TTY environments automatically and switches to CI mode:
- Rich structured logging instead of Textual TUI.
- JSON event stream on `--json-events` flag.
- Exit code 0 = no CRITICAL or HIGH findings (configurable).
- Exit code 1 = CRITICAL or HIGH findings present.
- Exit code 2 = scan error or safety violation.

### CI Exit Code Configuration

```yaml
# bughunter-scope.yml (CI section)
ci:
  fail_on_tier: high        # fail if any HIGH or CRITICAL findings
  fail_on_score: 70         # fail if any finding VulnScore >= 70
  fail_on_cost_usd: 0.50    # fail if estimated cost exceeds threshold
  auto_approve: false        # require manual approval gates even in CI
```

### GitHub Actions Example

```yaml
# .github/workflows/bughunter-scan.yml
name: Bug Hunter CLI Security Scan

on:
  pull_request:
    branches: [main]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install Bug Hunter CLI
        run: uv tool install bughunter

      - name: Run security scan
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          bughunter scan \
            --scope bughunter-scope.yml \
            --auto-approve \
            --json-events > bughunter-events.json

      - name: Export SARIF
        if: always()
        run: bughunter export --run $(cat .bughunter/last-run-id) --format sarif

      - name: Upload SARIF to GitHub Code Scanning
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: .bughunter/runs/*/bug-report.sarif
```

---

## GitHub Issue Export

```bash
# Export a specific finding as a GitHub issue (requires GITHUB_TOKEN)
bughunter github-issue --run abc123 --finding f001

# Export all CRITICAL and HIGH findings as GitHub issues
bughunter github-issue --run abc123 --tier critical high
```

**Issue format**:
- Title: `[Security] SQL Injection in auth/views.py (CRITICAL - Score: 94)`
- Labels: `security`, `critical`, `sql-injection`
- Body: Full finding detail with score breakdown, reproduction steps, fix guidance
- Includes a `[Bug Hunter CLI]` footer with run ID and scan date

Requires `GITHUB_TOKEN` environment variable. The tool only creates issues — it does not read or modify existing issues.

---

## Plugin Test Packs

Organisations can add custom test definitions without modifying the core tool.

### Plugin Structure

```
~/.bughunter/plugins/
  my-org-tests/
    plugin.json
    tests/
      custom-auth-check.yml
      internal-api-check.yml
```

`plugin.json`:
```json
{
  "name": "my-org-tests",
  "version": "1.0.0",
  "description": "Custom security tests for our internal API patterns",
  "author": "security@myorg.com",
  "tests": ["tests/*.yml"]
}
```

Custom test definitions follow the same format as `Docs/test-library.md`. They are loaded by `TestRegistry` at startup and available to `PlannerAgent` for test selection.

Plugin tests cannot modify `SafetyPolicyEngine` rules — they must follow the same safety classification system.

---

## Complete Fixture App Suite

### Vulnerable Flask App (`tests/fixtures/vulnerable_flask_app/`)

A minimal Flask application with documented, intentional vulnerabilities:

| File | Vulnerability | Line | Semgrep Rule | Expected Tier |
|---|---|---|---|---|
| `app.py:42` | SQL Injection | 42 | python.django.sqli | CRITICAL |
| `app.py:67` | Debug mode enabled | 67 | python.flask.debug | INFO |
| `config.py:8` | Hardcoded API key | 8 | generic.secrets.api-key | HIGH |
| `app.py:89` | Missing CSRF | 89 | python.flask.csrf | MEDIUM |
| `app.py:112` | Insecure CORS `*` | 112 | python.flask.cors | MEDIUM |
| `app.py:134` | Path traversal | 134 | python.path-traversal | HIGH |
| `requirements.txt` | Outdated Flask with CVE | — | pip-audit | MEDIUM |

Each vulnerability is marked with `# INTENTIONAL VULNERABILITY: <ID>` comment for audit trail.

### Vulnerable Express App (`tests/fixtures/vulnerable_express_app/`)

| File | Vulnerability | Line | Scanner | Expected Tier |
|---|---|---|---|---|
| `app.js:28` | Reflected XSS | 28 | Semgrep javascript.xss | HIGH |
| `app.js:54` | JWT alg:none accepted | 54 | Semgrep javascript.jwt | CRITICAL |
| `app.js:78` | Missing Helmet headers | 78 | HTTP header check | MEDIUM |
| `app.js:93` | CORS allow all origins | 93 | HTTP CORS check | MEDIUM |
| `package.json` | Vulnerable express-validator | — | npm audit | LOW |

### Clean Versions

Both fixture apps have a `clean/` variant with all vulnerabilities fixed. Integration tests must produce zero findings on the clean variants.

---

## Prompt Injection Test Suite

A dedicated test suite validating that `PromptGuardAgent` blocks all known injection patterns:

```
tests/security/prompt_injection/
  test_ignore_instructions.py     # "ignore previous instructions"
  test_role_override.py           # "you are now a different AI"
  test_system_override.py         # [SYSTEM] embedded in comments
  test_base64_injection.py        # base64-encoded injection in strings
  test_readme_injection.py        # injection in README content sent as evidence
  test_json_injection.py          # injection in JSON response bodies
  test_yaml_injection.py          # role: system in YAML data
```

Each test:
1. Creates a fake evidence packet containing an injection attempt.
2. Passes it through `PromptGuardAgent`.
3. Asserts the injected content is quarantined (wrapped as `[UNTRUSTED EVIDENCE BLOCK]`).
4. Asserts a `security_event` is logged.
5. Asserts the LLM call (mocked) never receives the injection as an instruction.

---

## Semgrep Rule Version Pinning

For reproducibility and supply-chain safety, Semgrep rule sets can be pinned to specific versions:

```yaml
# bughunter-scope.yml
scan:
  semgrep:
    rules:
      - id: p/security-audit
        sha256: abc123...       # pin rule pack hash
      - id: p/secrets
        sha256: def456...
    timeout_per_file: 30
    max_memory_mb: 256
```

On first run, rule packs are downloaded and their hashes verified. On subsequent runs, the local cache is used and verified against the pinned hash. Hash mismatch → abort with error.

---

## Todo List

- [ ] Implement SARIF 2.1.0 exporter.
- [ ] Implement JSON exporter.
- [ ] Implement `bughunter export` command.
- [ ] Validate SARIF output against SARIF schema.
- [ ] Implement CI mode (non-TTY detection, exit codes).
- [ ] Implement CI exit code configuration from `bughunter-scope.yml`.
- [ ] Create GitHub Actions workflow example.
- [ ] Implement `bughunter github-issue` command.
- [ ] Implement plugin test pack loader in `TestRegistry`.
- [ ] Create complete vulnerable Flask fixture app with documented vuln map.
- [ ] Create complete vulnerable Express fixture app with documented vuln map.
- [ ] Create clean versions of both fixture apps.
- [ ] Write integration tests: fixture apps produce expected findings.
- [ ] Write integration tests: clean fixture apps produce zero findings.
- [ ] Write prompt injection test suite.
- [ ] Implement Semgrep rule version pinning.
- [ ] Add `--auto-approve` flag for CI mode.
- [ ] Add `--json-events` flag for machine consumption.
- [ ] Add cost control CI enforcement.

---

## Acceptance Criteria

Phase 5 is complete when:

- SARIF export passes schema validation.
- GitHub Actions example runs without errors.
- CI mode produces correct exit codes based on findings.
- Plugin test packs are loaded and available to `PlannerAgent`.
- Fixture apps produce all expected findings (with ±1 tier tolerance).
- Clean fixture apps produce zero findings.
- Prompt injection test suite passes: all patterns quarantined, zero leaked instructions.
- Semgrep rule pinning works: hash mismatch causes abort.
- `bughunter github-issue` creates properly formatted issues.
