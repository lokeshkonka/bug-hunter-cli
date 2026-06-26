# Phase 1: Foundation, Safety, and CLI Skeleton

## Goal

Create the project foundation for Bug Hunter CLI. Phase 1 should make the tool installable, configurable, safe by default, and capable of producing a minimal structured scan report from deterministic local checks. It also introduces the Semgrep runner, the `SafetyPolicyEngine`, and a basic streaming TUI.

This phase does not need full AI autonomy or the Textual TUI. It establishes the architecture that later phases build on.

---

## Deliverables

- Python package scaffold using `uv` and `pyproject.toml`.
- `bughunter` CLI entrypoint using Typer.
- Basic Rich-based streaming TUI (Textual upgrade deferred to Phase 3).
- `bughunter-scope.yml` parser and validator.
- Provider config model for OpenAI and Gemini.
- SQLite database with full schema (all tables pre-created).
- Event bus (asyncio-based, used by TUI and all agents).
- `Finding`, `Evidence`, `Report`, `PolicyDecision`, `PolicyViolation` schemas.
- `SafetyPolicyEngine` central enforcement.
- `SecretRedactor` for masking secrets before storage, display, or LLM calls.
- Minimal Semgrep runner (secrets + debug flag rules only in Phase 1).
- Minimal deterministic checks: secrets, debug flags, env templates, missing headers.
- Minimal Markdown report renderer.
- Tests for scope validation, safety policy blocking, and report rendering.

---

## Commands To Support

```bash
bughunter
bughunter config
bughunter scan --scope bughunter-scope.yml
bughunter report --run <run_id>
bughunter runs
```

---

## Scope File

```yaml
project:
  name: example-app
  repo_path: .

targets:
  urls:
    - http://localhost:3000
  hosts: []

scan:
  mode: safe-active
  max_requests_per_minute: 60
  max_depth: 2
  max_concurrency: 5

safety:
  allow_lab_validation: false
  prompt_injection_sensitivity: medium
  notes: "Authorized local development target"

cost:
  max_tokens_per_run: 200000
  max_tokens_per_test: 15000
  max_cost_usd: 1.00
  warn_at_percent: 80
```

**Validation rules**:

- Network scans require at least one URL or host.
- URLs must be explicit; no wildcard internet scanning.
- `safe-active` is the default scan mode.
- `lab-validation` requires `allow_lab_validation: true`.
- Out-of-scope hosts must be blocked before any request is made.
- `max_cost_usd` must be a positive float.

---

## SQLite Schema (All Tables Created in Phase 1)

All tables are created upfront in Phase 1, even if not fully populated until later phases. This prevents schema migration issues.

```sql
-- Core run tracking
CREATE TABLE runs (
    id TEXT PRIMARY KEY, status TEXT, scope_path TEXT,
    created_at TEXT, completed_at TEXT, token_budget INTEGER, cost_budget_usd REAL
);
CREATE TABLE events (
    id TEXT PRIMARY KEY, run_id TEXT, type TEXT, agent TEXT,
    message TEXT, metadata TEXT, created_at TEXT
);
CREATE TABLE targets (
    id TEXT PRIMARY KEY, run_id TEXT, url TEXT, host TEXT, scope_mode TEXT
);
CREATE TABLE files (
    id TEXT PRIMARY KEY, run_id TEXT, path TEXT, language TEXT,
    relevance_score REAL, excluded INTEGER, excluded_reason TEXT
);

-- Index
CREATE TABLE index_entries (
    id TEXT PRIMARY KEY, run_id TEXT, file_id TEXT, symbol TEXT,
    line_start INTEGER, line_end INTEGER, security_relevance TEXT,
    tags TEXT, test_category TEXT, semgrep_rule_ids TEXT
);

-- Tests
CREATE TABLE test_plans (
    id TEXT PRIMARY KEY, run_id TEXT, title TEXT, category TEXT,
    safety_class TEXT, target TEXT, plan_path TEXT, created_at TEXT
);
CREATE TABLE test_results (
    id TEXT PRIMARY KEY, run_id TEXT, test_plan_id TEXT, status TEXT,
    tools_run TEXT, evidence_ids TEXT, finding_ids TEXT, created_at TEXT
);

-- Safety
CREATE TABLE policy_decisions (
    id TEXT PRIMARY KEY, run_id TEXT, action TEXT, target TEXT,
    decision TEXT, reason TEXT, created_at TEXT
);
CREATE TABLE policy_violations (
    id TEXT PRIMARY KEY, run_id TEXT, action TEXT, target TEXT,
    reason TEXT, created_at TEXT
);
CREATE TABLE security_events (
    id TEXT PRIMARY KEY, run_id TEXT, event_type TEXT, source_file TEXT,
    source_line INTEGER, pattern TEXT, confidence TEXT, content_hash TEXT,
    detected_at TEXT, action_taken TEXT
);

-- Evidence and findings
CREATE TABLE evidence (
    id TEXT PRIMARY KEY, run_id TEXT, test_plan_id TEXT, source_tool TEXT,
    source_file TEXT, line_start INTEGER, line_end INTEGER,
    observation TEXT, metadata TEXT, created_at TEXT
);
CREATE TABLE findings (
    id TEXT PRIMARY KEY, run_id TEXT, title TEXT, severity TEXT,
    confidence TEXT, category TEXT, affected_component TEXT,
    evidence_ids TEXT, impact TEXT, reproduction_steps TEXT,
    recommendation TEXT, retest_steps TEXT, status TEXT, created_at TEXT
);
CREATE TABLE score_components (
    id TEXT PRIMARY KEY, finding_id TEXT, run_id TEXT,
    cvss_score REAL, cvss_vector TEXT, cvss_rationale TEXT,
    ai_prob REAL, ai_prob_rationale TEXT,
    evidence_weight REAL, evidence_items TEXT,
    exploit_factor REAL, exploit_rationale TEXT,
    remed_penalty REAL, remed_rationale TEXT,
    vuln_score REAL, risk_tier TEXT,
    computed_at TEXT, inflation_flag INTEGER DEFAULT 0
);

-- Reports and providers
CREATE TABLE reports (
    id TEXT PRIMARY KEY, run_id TEXT, format TEXT, path TEXT, created_at TEXT
);
CREATE TABLE provider_usage (
    id TEXT PRIMARY KEY, run_id TEXT, agent TEXT, test_id TEXT,
    model TEXT, prompt_tokens INTEGER, completion_tokens INTEGER,
    total_tokens INTEGER, estimated_cost_usd REAL, cached INTEGER, called_at TEXT
);
CREATE TABLE retest_runs (
    id TEXT PRIMARY KEY, original_run_id TEXT, created_at TEXT,
    findings_selected TEXT, results_summary TEXT, report_path TEXT
);
```

---

## Data Models (Pydantic)

Define typed Pydantic v2 models for all core entities:

- `Run`, `Scope`, `Target`, `Event`
- `Evidence`, `Finding`, `Report`
- `ProviderConfig`, `SafetyPolicy`
- `PolicyDecision`, `PolicyViolation`
- `SecurityEvent`
- `ScoreComponents` (stub in Phase 1, populated in Phase 4)

All models use `model_config = ConfigDict(frozen=True)` to prevent mutation after creation.

---

## Event Streaming

Implement a single internal async event bus used by CLI, TUI, and all agents.

**Required event fields**:

- `run_id`
- `timestamp`
- `type`
- `agent`
- `message`
- `metadata` (dict)

**Phase 1 event types**:

- `phase_started`
- `phase_completed`
- `tool_started`
- `tool_progress`
- `tool_completed`
- `observation`
- `finding_candidate`
- `finding_confirmed`
- `finding_rejected`
- `report_written`
- `policy_violation`
- `security_event`
- `error`
- `budget_warning`

---

## Semgrep Integration (Phase 1 Subset)

Phase 1 introduces the Semgrep runner with a limited rule subset:

- `p/secrets` — API keys, tokens, private keys
- Debug flag patterns — `DEBUG=True`, `debug=True` in config files
- Environment template detection — `.env.example`, `.env.template`

The full Semgrep integration (all language packs) is completed in Phase 2.

**Semgrep runner requirements**:
- Auto-detect if Semgrep is installed. If not, prompt user to install or offer to install.
- Run with `--json` output flag.
- Parse output as `SemgrepResult` Pydantic model.
- Apply per-file timeout (30s default).
- Store each match as an `Evidence` record with source_tool=`semgrep`, rule_id, file, lines.

---

## SafetyPolicyEngine

Central `SafetyPolicyEngine` used by all agents. Must be in place before any scan runs.

**Responsibilities**:
- Validate target scope against `bughunter-scope.yml`.
- Classify tests as `passive`, `safe-active`, `lab-validation`, or `blocked`.
- Block out-of-scope network targets (reject before request is sent).
- Block destructive payload categories.
- Record blocked actions as `PolicyViolation` records.
- Redact secret-like values before display or model calls (delegates to SecretRedactor).
- Emit `policy_violation` events for all blocked actions.

**Policy decisions**: `allow`, `allow_with_limits`, `downgrade`, `block`

**Every action produces a decision** — no silent passes.

---

## Minimal Deterministic Checks (Phase 1)

Phase 1 checks (deterministic only, no LLM required):

1. **Secret detection**: Run Semgrep `p/secrets` against all non-excluded files. Also check for `.env` files containing values (not just templates).
2. **Debug flag detection**: Regex + Semgrep patterns for `DEBUG=True`, `APP_ENV=development`, `NODE_ENV=development` in config files.
3. **Environment template detection**: Detect `.env.example` and `.env.template` files. Check if a corresponding real `.env` is committed to the repo.
4. **Missing security headers**: If a scoped URL is provided, make a single GET request and check for: `Content-Security-Policy`, `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`, `Permissions-Policy`.
5. **Risky config flags**: Detect `ALLOW_ALL_CORS`, `DISABLE_AUTH`, `SKIP_VERIFICATION` style flags in config files.

AI is optional in Phase 1. If provider config exists, it can summarize deterministic findings, but it must not invent findings without evidence.

---

## Phase 1 TUI (Rich-based)

A simple Rich-based streaming display. Upgraded to full Textual in Phase 3.

**Phase 1 TUI shows**:
- Run status (started, scanning, completed)
- Current phase name
- Recent events (scrolling log, max 20 lines)
- Finding count by severity (CRITICAL: 0, HIGH: 0, ...)
- Report path on completion
- Spinner for long operations

**Rules**:
- Never displays chain-of-thought reasoning.
- All events from the event bus are streamed to the console.

---

## SecretRedactor

`SecretRedactor` runs on all text before it is:
- Stored in SQLite (store masked version + SHA256 hash only)
- Displayed in TUI
- Sent to LLM provider

**Redaction rules**:
- Mask: `sk-***`, `ghp_***`, `AIza***` style patterns
- Store: `REDACTED:sha256:<hash>` in place of actual value
- Mark the file and line where the secret was found
- Emit a `finding_candidate` event for the secret exposure

---

## Todo List

- [ ] Create `pyproject.toml` with `uv` and CLI entrypoint.
- [ ] Add package structure under `bughunter/`.
- [ ] Implement Typer CLI with all Phase 1 commands.
- [ ] Implement scope file loader, validator, and Pydantic model.
- [ ] Implement provider config model (OpenAI and Gemini).
- [ ] Create SQLite schema with all tables.
- [ ] Implement `RunStore` with run creation and lookup.
- [ ] Implement async event bus.
- [ ] Implement `Finding`, `Evidence`, `PolicyDecision` Pydantic schemas.
- [ ] Implement `SafetyPolicyEngine` with scope validation and blocking.
- [ ] Implement `SecretRedactor`.
- [ ] Implement Semgrep runner (Phase 1 rule subset).
- [ ] Implement minimal deterministic checks (secrets, debug, headers).
- [ ] Implement minimal Markdown report renderer.
- [ ] Implement Rich-based streaming TUI.
- [ ] Add tests: scope validation, safety policy blocking, Semgrep runner, secret redaction, report rendering.
- [ ] Add README quickstart section.

---

## Acceptance Criteria

Phase 1 is complete when:

- `bughunter scan --scope bughunter-scope.yml` creates a run, runs Semgrep, and produces a report.
- Out-of-scope URLs are blocked by `SafetyPolicyEngine` before any request.
- Semgrep findings are stored as evidence records with rule IDs and line ranges.
- Detected secrets are redacted in storage, TUI, and any model calls.
- `bughunter report --run <run_id>` writes a valid Markdown report.
- The terminal shows streaming progress events from the event bus.
- All tests pass: scope, storage, safety, Semgrep runner, redaction, report.
