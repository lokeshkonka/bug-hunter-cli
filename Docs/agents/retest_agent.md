# RetestAgent

## Identity

**Name**: RetestAgent  
**Role**: Dedicated retest workflow, fix validation, and finding status lifecycle management  
**Phase**: Runs on demand via `bughunter retest --run <run_id>` command  
**LangGraph node**: `retest_findings` (separate graph from main scan)  

---

## Purpose

RetestAgent manages the full lifecycle of a finding after initial discovery. When a developer claims they have fixed a vulnerability, RetestAgent:

1. Loads the original scope, test plan, and evidence from the prior run.
2. Re-runs only the specific tests relevant to the selected findings.
3. Compares new evidence against original evidence.
4. Updates finding status: `fixed`, `still_present`, `partially_fixed`, `not_retested`, or `inconclusive`.
5. Generates a retest report section that can be appended to the original `bug-report.md` or exported separately.

This closes the loop between security finding and developer remediation — the most critical part of a professional security workflow.

---

## Retest Command

```bash
# Retest all findings from a run
bughunter retest --run abc123

# Retest specific findings
bughunter retest --run abc123 --finding f001 f002

# Retest only HIGH and CRITICAL findings
bughunter retest --run abc123 --tier high critical

# Retest with updated scope (if target URL changed)
bughunter retest --run abc123 --scope updated-scope.yml
```

---

## Retest Workflow

### Step 1: Load Prior Run

RetestAgent loads from SQLite:
- Original `Scope` record
- All `Finding` records matching the selection filter
- All `Evidence` records for selected findings
- All `TestPlan` records that produced those findings
- Original `score_components` for baseline comparison

### Step 2: Verify Scope

The original scope is re-validated. If the target URL or repo path has changed, the user is prompted to confirm the updated scope. The retest will not proceed against unauthorized targets.

### Step 3: Selective Test Re-execution

For each selected finding:

1. Look up the original `test_plan` that produced the finding.
2. Identify the deterministic tools that were used (Semgrep rules, HTTP checks, etc.).
3. Re-run only those tools against the same targets.
4. Collect new evidence.

Retest does **not** re-run the full scan. It only re-runs tests directly relevant to the selected findings. This keeps retest fast (seconds to minutes instead of a full scan).

### Step 4: Evidence Comparison

RetestAgent compares new evidence against original:

| Scenario | New Status |
|---|---|
| Original Semgrep match no longer present | `fixed` (tentative) |
| Original HTTP proof no longer reproducible | `fixed` (tentative) |
| Both original evidences gone, static code changed | `fixed` (confirmed) |
| Same Semgrep match still present | `still_present` |
| Same HTTP behavior still observed | `still_present` |
| Semgrep gone but HTTP proof persists | `partially_fixed` |
| Tool ran but produced no comparable output | `inconclusive` |
| Tool could not run (scope changed, target down) | `not_retested` |

### Step 5: Score Update

VulnScoringAgent re-scores fixed or partially-fixed findings. Fixed findings get `vuln_score: 0` and `risk_tier: resolved`. The new score record is stored alongside the original for comparison.

### Step 6: Retest Report

RetestAgent generates a retest section:

```markdown
## Retest Report — Run abc123 — 2026-06-25

**Retest date**: 2026-06-25  
**Original scan**: 2026-06-20  
**Findings retested**: 4  

| Finding | Original Score | Status | New Score |
|---|---|---|---|
| SQL Injection (auth/views.py:142) | 94 CRITICAL | ✅ Fixed | 0 Resolved |
| Missing Auth (/api/admin) | 72 HIGH | ❌ Still Present | 71 HIGH |
| XSS (/search?q=) | 51 MEDIUM | ✅ Fixed | 0 Resolved |
| Hardcoded JWT Secret | 88 CRITICAL | ⚠️ Partially Fixed | 45 MEDIUM |

### Finding: SQL Injection — Fixed
**Original evidence**: Semgrep rule python.django.sqli at auth/views.py:142. HTTP POST /api/login returned 500.  
**Retest evidence**: Semgrep match no longer present. auth/views.py:142 now uses parameterized query. HTTP POST returns 200.  
**Conclusion**: Fixed. Parameterized query correctly applied.

### Finding: Missing Auth — Still Present
**Original evidence**: HTTP GET /api/admin returned 200 without Authorization header.  
**Retest evidence**: Same behavior observed. Route still accessible without authentication.  
**Conclusion**: Not fixed. Recommend adding authentication middleware.
```

---

## Finding Status Lifecycle

```
[new]
  │
  ├─→ finding_candidate   (static scanner match, not yet confirmed)
  │
  ├─→ finding_confirmed   (deterministic evidence present)
  │       │
  │       ├─→ still_present      (retest: same evidence found)
  │       ├─→ partially_fixed    (retest: some evidence gone)
  │       ├─→ fixed              (retest: all evidence gone)
  │       ├─→ inconclusive       (retest: tool ran, unclear result)
  │       └─→ not_retested       (retest: tool could not run)
  │
  └─→ rejected            (zero evidence, rejected by VulnScoringAgent)
```

---

## Safety Rules for Retesting

- Retest uses the same scope as the original run. It cannot expand scope.
- If the original target URL is no longer available, RetestAgent marks the finding as `not_retested` rather than failing silently.
- Race-condition and business-logic retests still require the same approval gates as the original run.
- Retest results are always stored as a new run record, linked to the original. The original run data is never modified.

---

## Retest Run Record

```sql
CREATE TABLE retest_runs (
    id              TEXT PRIMARY KEY,
    original_run_id TEXT NOT NULL REFERENCES runs(id),
    created_at      TEXT NOT NULL,
    findings_selected TEXT NOT NULL,  -- JSON array of finding IDs
    results_summary TEXT NOT NULL,    -- JSON: {fixed: n, still_present: n, ...}
    report_path     TEXT
);
```
