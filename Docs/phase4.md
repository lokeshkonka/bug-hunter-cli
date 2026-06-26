# Phase 4: Orchestration, Scoring, Reports, and Retesting

## Goal

Connect all components into a complete autonomous workflow using LangGraph. Phase 4 delivers:

- Full LangGraph graph with all 12 agents
- `VulnScoringAgent` — composite VulnScore, risk tiers, probability calibration
- `FixAgent` — concrete remediation guidance and patch-style suggestions
- `ReportAgent` — polished `bug-report.md` from all stored artifacts
- `RetestAgent` — dedicated retest workflow and finding lifecycle
- OpenAI and Gemini provider adapters with full structured output
- Score breakdown modal in TUI
- End-to-end integration tests

---

## Deliverables

- LangGraph state model and graph definition.
- All agent nodes wired into the graph.
- `VulnScoringAgent` with composite formula, calibration, and inflation detection.
- `FixAgent` with per-finding remediation guidance.
- `ReportAgent` with all required sections and SARIF stub.
- `RetestAgent` with retest workflow, evidence comparison, and status lifecycle.
- OpenAI provider adapter.
- Gemini provider adapter.
- Score breakdown modal in Textual TUI.
- Token and cost tracking (full `provider_usage` table populated).
- End-to-end tests against both fixture apps.

---

## LangGraph Graph

### State Model

```python
class BugHunterState(TypedDict):
    run_id: str
    scope: Scope
    manifest: RepositoryManifest
    index: CodebaseIndex
    test_plans: list[TestPlan]
    static_findings: list[FindingCandidate]
    dynamic_findings: list[FindingCandidate]
    evidence: list[Evidence]
    scored_findings: list[ScoredFinding]
    fix_guidance: dict[str, FixGuidance]    # finding_id → guidance
    report_path: str
    phase: str
    errors: list[str]
    approval_states: dict[str, bool]         # gate_id → approved
    token_usage: TokenUsage
    inflation_flag: bool
```

### Graph Flow

```
load_scope → validate_safety → create_run
    → planner_plan
    → recon_build_manifest
    → recon_build_index
    → context_filter_files
    → planner_generate_test_plans    (writes testN.md)
    → [APPROVAL GATE: safe-active]   (if dynamic tests requested)
    → static_audit                   (Semgrep + AI review)
    → dynamic_test                   (if targets present and approved)
    → evidence_normalize
    → score_findings                 (VulnScoringAgent)
    → fix_generate                   (FixAgent)
    → report_write                   (ReportAgent → bug-report.md)
    → retest_offer                   (optional, interactive)
    → END
```

**Conditional edges**:
- Skip `dynamic_test` node if no URLs are in scope.
- Skip `[APPROVAL GATE]` in non-interactive (CI) mode with `--auto-approve` flag.
- Skip `retest_offer` in non-interactive mode.

### Checkpointing

LangGraph checkpoints state after each node completion. Checkpoints are stored in SQLite via a custom `BugHunterCheckpointer`. The `scan --resume` command loads the last checkpoint and replays from the next uncompleted node.

---

## VulnScoringAgent (Full Implementation)

See `Docs/agents/vuln_scoring_agent.md` for the full specification.

### Phase 4 Deliverables

- [ ] Implement VulnScoringAgent LangGraph node.
- [ ] CVSS vector proposal via structured LLM output (Pydantic model).
- [ ] AI confidence calibration rules (all categories).
- [ ] Evidence weight computation from `EvidenceAgent` output.
- [ ] Exploitability factor computation from index metadata.
- [ ] Remediation penalty from `FixAgent` (blocking call within node).
- [ ] Composite VulnScore formula (deterministic Python, not LLM).
- [ ] Inflation detection: mean confidence > 0.75 → `score_inflation_warning`.
- [ ] Write to `score_components` table (immutable records).
- [ ] Emit `finding_scored` events to TUI.
- [ ] Score breakdown modal in Textual TUI.
- [ ] Finding ranking by VulnScore.

---

## FixAgent

`FixAgent` provides concrete remediation guidance for every confirmed finding.

### Responsibilities

1. Receives a scored finding with evidence and index entry.
2. Requests targeted code snippet for the affected location.
3. Asks LLM to propose a specific fix in the detected language/framework.
4. Formats fix as:
   - Human-readable description
   - Patch-style diff (where applicable)
   - Framework-specific best practice reference
   - OWASP remediation reference
5. Assesses remediation complexity (`trivial`, `simple`, `moderate`, `hard`, `very_hard`).
6. Returns complexity to `VulnScoringAgent` for the remediation penalty.
7. Writes fix guidance to SQLite.

### Patch-Style Output (when applicable)

```diff
# auth/views.py:142
- result = db.execute(f"SELECT * FROM users WHERE id = {user_id}")
+ result = db.execute("SELECT * FROM users WHERE id = %s", [user_id])
```

### Framework-Specific Guidance

FixAgent is aware of framework patterns and proposes fixes in the idiom of the detected stack:

- Django: `User.objects.get(id=user_id)` (ORM parameterization)
- Flask/SQLAlchemy: `db.session.execute(select(User).where(User.id == user_id))`
- Express: `db.query('SELECT * FROM users WHERE id = ?', [userId])`
- Spring: `jdbcTemplate.queryForObject("... WHERE id = ?", Integer.class, userId)`

---

## ReportAgent

`ReportAgent` generates `bug-report.md` from **stored artifacts only** — never from model memory.

### Report Generation Process

1. Load `index.md` and extract summary section.
2. Load all `test_plans` for the run.
3. Load all `test_results` for the run.
4. Load all scored findings with score breakdowns.
5. Load all evidence records per finding.
6. Load all fix guidance records.
7. Load all policy violations.
8. Load all security events (prompt injection attempts).
9. Load token and cost summary from `provider_usage`.
10. Render `bug-report.md` using the template in `Docs/templates/bug-report-template.md`.

### Required Report Sections

1. **Executive Summary** — total findings by tier, scan mode, top risk
2. **Scope and Authorization** — scope file contents, authorization note
3. **Scan Mode and Safety Policy** — mode used, what was blocked
4. **Codebase Index Summary** — language/framework, file count, top risk areas
5. **Tests Executed** — table of all tests with status
6. **Blocked and Skipped Tests** — policy violations table
7. **AI Safety Events** — prompt injection attempts detected
8. **Risk Overview** — VulnScore distribution chart (ASCII), tier counts
9. **Findings Table** — sorted by VulnScore descending
10. **Detailed Findings** — one section per finding with full breakdown
11. **Retest Checklist** — ordered action list by finding
12. **Tool and Model Metadata** — Semgrep version + rules, provider + model, tokens, cost

### Per-Finding Section

```markdown
## [CRITICAL 94] SQL Injection — auth/views.py

**VulnScore**: 94 / 100  🔴 CRITICAL
**Category**: injection/sql
**Affected**: `auth/views.py:142` — `POST /api/login`
**Status**: confirmed
**Confidence**: confirmed (0.91)

### Score Breakdown
| Component | Value | Weight | Points |
|---|---|---|---|
| CVSS Base (AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N) | 8.1 | 35% | 2.84 |
| AI Confidence | 0.91 | 25% | 2.28 |
| Evidence Weight (4.5) | 4.5 | 20% | 1.80 |
| Exploit Factor | 0.80 | 12% | 0.96 |
| Remediation Penalty | -0.05 | 8% | -0.38 |
| **VulnScore** | | | **94** |

### Evidence
- E-001: Semgrep rule `python.django.security.audit.raw-query` at auth/views.py:142
- E-002: HTTP POST /api/login with canary returned 500 (behavioral difference)

### Reproduction Steps
1. Send: `POST /api/login` with body: `{"user_id": "1 AND 1=1--"}`
2. Observe: HTTP 500 Internal Server Error
3. Send: `POST /api/login` with body: `{"user_id": "1 AND 1=2--"}`
4. Observe: HTTP 200 (different response → SQL injection confirmed)

### Impact
Full authentication bypass possible. Attacker can log in as any user by injecting SQL logic.

### Recommended Fix
Use parameterized queries:
```diff
- result = db.execute(f"SELECT * FROM users WHERE id = {user_id}")
+ result = db.execute("SELECT * FROM users WHERE id = %s", [user_id])
```

### Retest Steps
1. Apply fix.
2. Run: `bughunter retest --run abc123 --finding f001`
3. Verify: Semgrep match no longer present, HTTP canary returns same response for both payloads.

**Source**: Index entry `IE-042` | Test plan `T-003` | Test result `TR-003` | Evidence `E-001, E-002`
```

---

## RetestAgent (Full Implementation)

See `Docs/agents/retest_agent.md` for the full specification.

### Phase 4 Deliverables

- [ ] Implement `bughunter retest` command.
- [ ] Implement `RetestAgent` LangGraph subgraph.
- [ ] Finding selection by ID, by tier, or all.
- [ ] Original scope and test plan reloading.
- [ ] Selective tool re-execution (only tools from original test).
- [ ] Evidence comparison and status determination.
- [ ] Score update for fixed and partially-fixed findings.
- [ ] Retest report generation and append/export.
- [ ] `retest_runs` table populated.

---

## Provider Adapters

### OpenAI Adapter

```python
class OpenAIAdapter(ProviderAdapter):
    def generate_structured(self, prompt, output_schema) -> BaseModel: ...
    def summarize(self, content, max_tokens) -> str: ...
    def rank_findings(self, findings) -> list[Finding]: ...
    def propose_fixes(self, finding, evidence) -> FixGuidance: ...
    def estimate_cost(self, prompt_tokens, completion_tokens) -> float: ...
```

- Models: `gpt-4o` (default), `gpt-4o-mini` (budget), configurable.
- Structured output via OpenAI function calling / JSON mode.
- Timeout: 60s. Retries: 3 with exponential backoff (1s, 4s, 16s).
- All calls go through `ProviderAdapter.send_with_guard()`.

### Gemini Adapter

- Models: `gemini-1.5-pro` (default), `gemini-1.5-flash` (budget), configurable.
- Structured output via Gemini response schema.
- Same timeout and retry policy.
- Same guard chain.

### Shared Rules

- API keys from environment variables: `OPENAI_API_KEY`, `GOOGLE_API_KEY`.
- Keys are never stored in config files or logged.
- `SecretRedactor` runs before all content is passed to the adapter.
- `PromptGuardAgent` wraps all content before adapter receives it.
- Usage tracked in `provider_usage` table per call.

---

## End-to-End Tests

Phase 4 requires end-to-end tests against both fixture apps.

### Test Scenarios

**Vulnerable Flask app** (expected findings):
- [ ] SQL injection in login route → CRITICAL, Semgrep + HTTP evidence
- [ ] Debug mode enabled → INFORMATIONAL, Semgrep evidence
- [ ] Hardcoded API key in config → HIGH, secrets scanner evidence
- [ ] Missing CSRF protection → MEDIUM, static analysis evidence
- [ ] Insecure CORS (`*`) → MEDIUM, HTTP header check evidence

**Vulnerable Express app** (expected findings):
- [ ] XSS in search route → HIGH, Semgrep + HTTP canary evidence
- [ ] Missing security headers → MEDIUM, HTTP header check evidence
- [ ] JWT `alg:none` acceptance → CRITICAL, static analysis evidence
- [ ] npm audit: outdated dependency with CVE → HIGH, `npm audit` evidence

**Validation criteria**:
- Each expected finding is produced with correct risk tier (±1 tier tolerance).
- Each finding has deterministic evidence (zero AI-only findings in test suite).
- No false positives on clean versions of the fixture apps.
- VulnScore distribution matches expected tier distribution.

---

## Todo List

- [ ] Implement LangGraph state model and graph definition.
- [ ] Implement `PlannerAgent` LangGraph node.
- [ ] Implement `ReconAgent` LangGraph node.
- [ ] Connect `ContextManagerAgent` utility into all nodes.
- [ ] Implement `StaticAuditAgent` LangGraph node.
- [ ] Implement `DynamicTestAgent` LangGraph node.
- [ ] Implement `EvidenceAgent` LangGraph node.
- [ ] Implement `VulnScoringAgent` LangGraph node (full scoring).
- [ ] Implement `FixAgent` LangGraph node.
- [ ] Implement `ReportAgent` LangGraph node (full bug-report.md).
- [ ] Implement OpenAI provider adapter.
- [ ] Implement Gemini provider adapter.
- [ ] Implement model timeout and retry policy.
- [ ] Implement full `provider_usage` tracking.
- [ ] Implement `RetestAgent` LangGraph subgraph.
- [ ] Implement `bughunter retest` command.
- [ ] Implement score breakdown modal in Textual TUI.
- [ ] Implement LangGraph checkpointer for resume support.
- [ ] Write end-to-end tests against fixture apps.
- [ ] Validate all expected findings are produced.
- [ ] Validate no false positives on clean fixtures.

---

## Acceptance Criteria

Phase 4 is complete when:

- `bughunter` can run an interactive end-to-end scan with the full LangGraph graph.
- OpenAI and Gemini can be selected and switched via `bughunter config`.
- Every finding has a VulnScore, risk tier, and score breakdown.
- `VulnScoringAgent` detects and flags score inflation.
- `FixAgent` provides language-specific remediation for every confirmed finding.
- `bug-report.md` includes all required sections, cites evidence IDs and index entries.
- Retest command works and produces a retest report.
- Score breakdown modal shows all 5 components in TUI.
- End-to-end tests pass against both fixture apps with expected findings and no false positives.
