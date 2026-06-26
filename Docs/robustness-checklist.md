# Robust Bug Hunter Checklist (Updated)

## Product Robustness

- [ ] Scope file is mandatory for network testing.
- [ ] Local repo-only passive scans work without network targets.
- [ ] `index.md` is created before test planning.
- [ ] `testing/testN.md` files are created before execution.
- [ ] `test-results.md` is updated after every test.
- [ ] `bug-report.md` is generated from artifacts and evidence only — not from model memory.
- [ ] Interrupted runs produce partial reports marked `[INCOMPLETE]`.
- [ ] Retesting reuses the original scope and test plan.
- [ ] Run resume (`--resume`) continues from the last LangGraph checkpoint.
- [ ] SARIF export passes schema validation.
- [ ] JSON export is machine-readable and parseable.
- [ ] CI mode produces correct exit codes.

## Safety Robustness

- [ ] Central `SafetyPolicyEngine` gates every command, request, payload, and test.
- [ ] Every test has `passive`, `safe-active`, `lab-validation`, or `blocked` classification.
- [ ] Destructive behavior is blocked by default across all modes.
- [ ] Race-condition tests have strict concurrency caps enforced in Python (not just prompt).
- [ ] File upload tests use benign files only.
- [ ] ZIP bomb and malware tests are blocked or lab-only simulations.
- [ ] Payment and business-logic tests require test data and explicit approval.
- [ ] Mobile certificate-pinning work is lab-only for owned apps and devices.
- [ ] Out-of-scope requests are blocked before they are sent (not after).
- [ ] Policy violations are recorded as `PolicyViolation` records — they never disappear silently.
- [ ] The tool never auto-upgrades from passive to active testing.
- [ ] Token and cost budgets are enforced by `ContextManagerAgent` — not just configured.

## AI Robustness

- [ ] All repository content and HTTP responses are treated as untrusted input.
- [ ] `PromptGuardAgent` wraps all untrusted content as evidence blocks before LLM calls.
- [ ] Prompt injection attempts in scanned files are quarantined and logged as `security_events`.
- [ ] Raw secrets are never sent to LLM providers — `SecretRedactor` runs first.
- [ ] Model calls receive bounded audit packets selected by `ContextManagerAgent`.
- [ ] Findings without deterministic evidence are rejected by `EvidenceAgent` (evidence gate).
- [ ] AI output is parsed as typed Pydantic models — never as raw strings blindly trusted.
- [ ] Provider timeouts are 60s max. Retries are bounded (3 max, exponential backoff).
- [ ] Token usage is tracked per run, per agent, and per test in `provider_usage` table.
- [ ] Token and cost budget hard limits are enforced — overrun switches to deterministic-only mode.

## Scoring Robustness

- [ ] Every confirmed finding has a VulnScore (0–100).
- [ ] VulnScore is computed by deterministic Python code — not by LLM output.
- [ ] CVSS vector is proposed by AI but validated against evidence type.
- [ ] AI confidence probability is capped based on evidence count (enforced in Python).
- [ ] AI confidence cannot exceed 0.80 without 2+ corroborating evidence items.
- [ ] Score inflation is detected: mean AI confidence > 0.75 across run triggers warning.
- [ ] Score components are stored immutably in `score_components` table.
- [ ] Reports cite exact score breakdown for every finding.
- [ ] Remediation complexity assessment comes from `FixAgent` — not from AI confidence.
- [ ] Zero-evidence findings receive VulnScore 0 and are rejected from the report.

## Semgrep Robustness

- [ ] Semgrep runs only against files in the repository manifest (excluded paths never touched).
- [ ] Per-file timeout (30s default) prevents hangs on large or obfuscated files.
- [ ] Semgrep output is parsed as structured JSON — never piped through `eval` or `exec`.
- [ ] Rule sets can be pinned to specific versions for reproducibility.
- [ ] Hash mismatch on pinned rules causes an abort — not silent continuation.
- [ ] Semgrep findings are the primary evidence source for static findings.
- [ ] AI reviews Semgrep matches for false-positive reduction — does not invent findings.

## Prompt Injection Robustness

- [ ] All content from scanned files is wrapped as evidence blocks.
- [ ] All HTTP response bodies are wrapped as evidence blocks.
- [ ] All log content and dependency metadata are wrapped as evidence blocks.
- [ ] `PromptGuardAgent` detects: "ignore previous instructions", "you are now", "system:", role-play assignments in comments.
- [ ] Base64-encoded injection patterns in large strings are checked.
- [ ] Injection attempts are logged as `security_events` (never silently ignored).
- [ ] Prompt injection test suite covers all known patterns (Phase 5).
- [ ] No tested injection pattern reaches the LLM as an instruction.

## Security Coverage

- [ ] Core web checks (headers, TLS, cookies, CORS, redirects).
- [ ] OWASP Web Top 10 checks.
- [ ] OWASP API Top 10 checks (BOLA, mass assignment, broken function auth).
- [ ] Authentication and session checks.
- [ ] Authorization and IDOR/BOLA checks.
- [ ] Business logic checks.
- [ ] Injection checks (SQL, NoSQL, SSTI, XXE, command, template, deserialization).
- [ ] File upload checks.
- [ ] Secret detection (Semgrep `p/secrets` + trufflehog patterns).
- [ ] Dependency and supply-chain checks (pip-audit, npm audit).
- [ ] Client-side checks (DOM XSS, CSP, LocalStorage leakage).
- [ ] Network and admin exposure checks.
- [ ] Cloud and infrastructure checks.
- [ ] Race-condition checks (with strict caps and explicit approval).
- [ ] Mobile API checks when scoped.
- [ ] Language and framework-specific checks (Django, Flask, Express, Spring, Laravel, Rails, Go).
- [ ] Whitebox source-code checks.
- [ ] Blackbox runtime checks.

## Reporting Robustness

- [ ] Findings include VulnScore, risk tier, and all 5 score components.
- [ ] Confirmed findings include deterministic evidence (Semgrep rule ID or HTTP proof).
- [ ] Reports separate confirmed bugs from likely, possible, and informational findings.
- [ ] Reports include exact reproduction steps.
- [ ] Reports include concrete fix guidance (language-specific, patch-style where possible).
- [ ] Reports include retest steps per finding.
- [ ] Reports cite index entry IDs, test plan IDs, test result IDs, and evidence IDs.
- [ ] Reports include blocked tests and skipped tests.
- [ ] Reports include AI safety events (prompt injection attempts).
- [ ] SARIF export passes schema validation (Phase 5).
- [ ] JSON export is parseable by standard JSON tools.
- [ ] CI exit codes are correct based on configured thresholds.

## TUI Robustness

- [ ] TUI shows live VulnScore and AI probability bars for every finding.
- [ ] TUI shows phase tracker with 8 phases and correct status icons.
- [ ] TUI shows agent feed without chain-of-thought reasoning.
- [ ] TUI shows score summary panel with tier counts and cost.
- [ ] Approval gate modals block the pipeline until user responds.
- [ ] Heartbeat events prevent TUI from appearing frozen.
- [ ] Rate limit countdown displays accurately.
- [ ] Interruption (Ctrl+C) prompts save before exit.
- [ ] Non-TTY fallback to Rich logging works correctly.
- [ ] Score breakdown modal shows all 5 components with rationale.
