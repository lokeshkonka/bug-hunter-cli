# Vulnerability Scoring System

## Purpose

Raw CVSS scores alone are insufficient for prioritizing security findings in an automated tool like Bug Hunter CLI. CVSS captures technical severity but ignores:

- How confident the AI actually is about the finding
- How much deterministic evidence backs the claim
- Whether the vulnerability is trivially exploitable in this specific context
- The cost and complexity of remediation

Bug Hunter CLI uses a **composite VulnScore (0–100)** that weights all of these dimensions. This gives developers and security engineers a more honest prioritization signal than CVSS alone.

The VulnScoringAgent computes this score for every finding before it appears in the TUI or the final report. Scores drive the live probability bars in the terminal and the severity ranking in `bug-report.md`.

---

## Scoring Components

The VulnScore is assembled from five components. Each component has a fixed weight. The weights are calibrated to balance technical severity with practical risk.

| Component | Weight | Range | Source |
|---|---|---|---|
| CVSS Base Score | 35% | 0.0 – 10.0 | Deterministic analysis + AI vector proposal |
| AI Confidence Probability | 25% | 0.0 – 1.0 | VulnScoringAgent calibrated output |
| Evidence Weight | 20% | 0 – 5 | EvidenceAgent from scanner outputs |
| Exploitability Factor | 12% | 0.0 – 1.0 | Computed from index + scanner metadata |
| Remediation Complexity Penalty | 8% | -0.15 – 0 | FixAgent assessment |

---

### Component 1: CVSS Base Score (35%)

**Range**: 0.0 to 10.0

The CVSS base score is computed from the standard CVSS v3.1 vector:

```
AV  = Attack Vector      (N=Network, A=Adjacent, L=Local, P=Physical)
AC  = Attack Complexity  (L=Low, H=High)
PR  = Privileges Required (N=None, L=Low, H=High)
UI  = User Interaction   (N=None, R=Required)
S   = Scope              (U=Unchanged, C=Changed)
C   = Confidentiality    (N=None, L=Low, H=High)
I   = Integrity          (N=None, L=Low, H=High)
A   = Availability       (N=None, L=Low, H=High)
```

**How it is computed in Bug Hunter CLI**:

1. Deterministic analysis (Semgrep matches, static code review, HTTP evidence) provides raw facts.
2. The StaticAuditAgent or DynamicTestAgent populates a structured evidence packet.
3. VulnScoringAgent proposes CVSS vector components based on the evidence packet.
4. The proposed vector is validated: if the finding is static-only (no runtime proof), AV cannot be set to N without explicit justification.
5. The final CVSS score is computed using the standard formula and stored immutably.

**Rules**:
- AI cannot assign a CVSS score above 7.0 for a static-only finding without a runtime corroboration flag.
- CVSS vector is always stored alongside its rationale in SQLite.
- Users can annotate (but not override) the CVSS vector after a run.

---

### Component 2: AI Confidence Probability (25%)

**Range**: 0.0 to 1.0

This is the VulnScoringAgent's calibrated estimate of how likely the finding is a true positive. It is **not** raw model logprob. It is a structured output field that the agent populates after reviewing all evidence.

**Calibration Rules**:

| Condition | Effect |
|---|---|
| Zero deterministic tool evidence | Probability capped at 0.40 |
| One tool match (e.g., Semgrep) | Probability capped at 0.75 |
| Two or more corroborating evidence items | Probability can reach up to 0.95 |
| Runtime HTTP proof present | +0.10 bonus (up to 0.95 cap) |
| Pattern is well-known (secrets, debug flags) | Starts at 0.85+ |
| Business logic finding | Capped at 0.70 without runtime proof |
| Race-condition finding | Capped at 0.65 without concurrency evidence |
| Historical scanner false-positive rate > 30% | Probability down-weighted by 0.15 |

**Per-Category Defaults**:

| Category | Default Probability Range |
|---|---|
| Secrets / API key detection | 0.85 – 0.95 |
| Dependency CVE | 0.80 – 0.95 |
| Hardcoded credentials | 0.75 – 0.90 |
| SQL injection (Semgrep match) | 0.60 – 0.80 |
| XSS (static) | 0.55 – 0.75 |
| IDOR / BOLA | 0.40 – 0.70 |
| Business logic | 0.30 – 0.65 |
| Race condition | 0.35 – 0.65 |
| SSRF (static) | 0.50 – 0.75 |

**Anti-Inflation Rule**:
- If AI confidence for a run averages above 0.80 across all findings, VulnScoringAgent flags a `score_inflation_warning` event.
- Users see this warning in the TUI score panel.

---

### Component 3: Evidence Weight (20%)

**Range**: 0 to 5 (capped)

Evidence weight is computed by EvidenceAgent before VulnScoringAgent receives the finding. Each piece of evidence adds to the weight score.

**Evidence Scoring Table**:

| Evidence Type | Points |
|---|---|
| Semgrep deterministic match (rule ID cited) | +2.0 |
| Runtime HTTP request + response proof | +2.0 |
| Secret pattern match with file + line context | +2.0 |
| Dependency CVE with advisory reference | +1.5 |
| Static code path analysis (data-flow trace) | +1.0 |
| Static + runtime corroboration (both present) | +0.5 bonus |
| Manual index annotation pointing to issue | +0.5 |
| AI inference without any tool match | +0.0 |
| **Maximum (capped)** | **5.0** |

**Rule**: A finding with zero evidence weight receives a VulnScore of 0 regardless of other components. Findings without evidence are rejected before scoring.

---

### Component 4: Exploitability Factor (12%)

**Range**: 0.0 to 1.0

The exploitability factor captures how easy it is to exploit this vulnerability in practice, independent of CVSS vectors.

**Scoring**:

| Criterion | Points |
|---|---|
| In OWASP Top 10 / OWASP API Top 10 | +0.30 |
| Public PoC or exploit tool available | +0.30 |
| Network-accessible without authentication | +0.20 |
| No user interaction required | +0.20 |

Maximum: 1.0 (capped). This factor is computed from index entry metadata, test category, and the finding's CVSS vector.

---

### Component 5: Remediation Complexity Penalty (8%)

**Range**: -0.15 to 0.0

Complex fixes that are unlikely to be deployed quickly receive a small downward adjustment to prevent score paralysis — where developers freeze because every finding looks equally urgent.

| Fix Complexity | Penalty |
|---|---|
| Trivial (config flag, env var) | -0.02 |
| Simple (1-3 line code change) | -0.05 |
| Moderate (function-level refactor) | -0.08 |
| Hard (architectural change) | -0.12 |
| Very Hard (framework migration) | -0.15 |

This penalty is assessed by FixAgent based on its remediation guidance. It does not change the true severity — it only adjusts urgency ordering.

---

## VulnScore Formula

```python
def compute_vuln_score(
    cvss: float,           # 0.0 - 10.0
    ai_prob: float,        # 0.0 - 1.0
    evidence_weight: float, # 0 - 5
    exploit_factor: float,  # 0.0 - 1.0
    remed_penalty: float,   # -0.15 - 0.0
) -> float:
    """
    Composite VulnScore normalized to 0-100.
    """
    # Weighted sum (raw max = 10*0.35 + 10*0.25 + 10*0.20 + 10*0.12 = 9.2 before penalty)
    raw = (
        (cvss * 0.35)
        + (ai_prob * 10 * 0.25)
        + (evidence_weight * 2 * 0.20)   # scale to 0-10
        + (exploit_factor * 10 * 0.12)
    )

    # Apply remediation penalty (as fraction of raw)
    adjusted = raw + (remed_penalty * raw)

    # Normalize to 0-100 (raw max ~9.2, min 0)
    normalized = (adjusted / 9.2) * 100

    return max(0.0, min(100.0, normalized))
```

### Worked Example 1: SQL Injection (HIGH)

```
CVSS:             8.1 (AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N)
AI Confidence:    0.82
Evidence Weight:  4.5 (Semgrep match + HTTP proof + data-flow trace)
Exploit Factor:   0.80 (OWASP Top 10 + no auth required)
Remed Penalty:   -0.05 (simple parameterized query fix)

raw = (8.1*0.35) + (0.82*10*0.25) + (4.5*2*0.20) + (0.80*10*0.12)
    = 2.835 + 2.05 + 1.80 + 0.96
    = 7.645

adjusted = 7.645 + (-0.05 * 7.645) = 7.263

VulnScore = (7.263 / 9.2) * 100 = 78.9  → HIGH
```

### Worked Example 2: Missing Security Header (LOW)

```
CVSS:             4.3 (AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:N/A:N)
AI Confidence:    0.92
Evidence Weight:  2.0 (HTTP header scan)
Exploit Factor:   0.30 (OWASP listed, trivial to check)
Remed Penalty:   -0.02 (single config line)

raw = (4.3*0.35) + (0.92*10*0.25) + (2.0*2*0.20) + (0.30*10*0.12)
    = 1.505 + 2.30 + 0.80 + 0.36
    = 4.965

adjusted = 4.965 + (-0.02 * 4.965) = 4.866

VulnScore = (4.866 / 9.2) * 100 = 52.9  → MEDIUM
```

---

## Risk Tiers

| Tier | Score Range | TUI Color | Report Badge | Action |
|---|---|---|---|---|
| CRITICAL | 85 – 100 | `bright_red` | 🔴 CRITICAL | Immediate fix, block deployment |
| HIGH | 65 – 84 | `dark_orange` | 🟠 HIGH | Fix before next release |
| MEDIUM | 40 – 64 | `yellow3` | 🟡 MEDIUM | Fix in current sprint |
| LOW | 15 – 39 | `steel_blue` | 🔵 LOW | Fix when convenient |
| INFORMATIONAL | 0 – 14 | `grey50` | ⚪ INFO | Hardening recommendation |

---

## VulnScoringAgent Responsibilities

VulnScoringAgent is a dedicated LangGraph node that runs after EvidenceAgent completes.

**Input**: Normalized finding from EvidenceAgent with all evidence records attached.

**Process**:
1. Validate evidence weight is non-zero (reject if zero).
2. Look up historical false-positive rate for this scanner + category combination.
3. Apply calibration rules to AI confidence probability.
4. Request CVSS vector proposal from provider (structured output).
5. Compute exploitability factor from index metadata and finding category.
6. Request remediation complexity from FixAgent.
7. Compute composite VulnScore.
8. Check for score inflation (mean confidence > 0.80 across all findings in this run).
9. Write all components + rationale to `score_components` SQLite table.
10. Emit `finding_scored` event to CliUiAgent for TUI update.
11. Pass ranked finding to ReportAgent.

**Output**: Scored finding with `vuln_score`, `risk_tier`, `score_breakdown`, `score_rationale`.

---

## TUI Score Display

The CliUiAgent renders scoring data in real time as VulnScoringAgent emits `finding_scored` events.

**Finding Card (in Live Findings panel)**:
```
┌─────────────────────────────────────────────┐
│ 🔴 CRITICAL  SQL Injection in auth/views.py  │
│ VulnScore: ████████████░░  94 / 100          │
│ AI Confidence: ██████████  0.91 (91%)        │
│ Evidence: 3 items  |  Exploit: OWASP + NoAuth│
└─────────────────────────────────────────────┘
```

**Score Summary Panel (right side)**:
```
┌─────────────────────┐
│  RISK SUMMARY       │
│  🔴  1  CRITICAL    │
│  🟠  2  HIGH        │
│  🟡  3  MEDIUM      │
│  🔵  0  LOW         │
│  ⚪  1  INFO        │
│                     │
│  Top Score: 94      │
│  Mean Score: 63.2   │
│  Inflation: OK      │
└─────────────────────┘
```

**Probability Bar Animation**: As VulnScoringAgent processes a finding, the AI Confidence bar animates from 0 to the final probability value over 0.8 seconds. This makes the AI reasoning process visible and builds trust.

---

## Score Audit Trail

Every score component is immutable once stored. The `score_components` SQLite table has the following schema:

```sql
CREATE TABLE score_components (
    id              TEXT PRIMARY KEY,
    finding_id      TEXT NOT NULL REFERENCES findings(id),
    run_id          TEXT NOT NULL,
    cvss_score      REAL NOT NULL,
    cvss_vector     TEXT NOT NULL,
    cvss_rationale  TEXT NOT NULL,
    ai_prob         REAL NOT NULL,
    ai_prob_rationale TEXT NOT NULL,
    evidence_weight REAL NOT NULL,
    evidence_items  TEXT NOT NULL,   -- JSON list of evidence IDs
    exploit_factor  REAL NOT NULL,
    exploit_rationale TEXT NOT NULL,
    remed_penalty   REAL NOT NULL,
    remed_rationale TEXT NOT NULL,
    vuln_score      REAL NOT NULL,
    risk_tier       TEXT NOT NULL,
    computed_at     TEXT NOT NULL,
    inflation_flag  INTEGER DEFAULT 0
);
```

Reports cite the `score_components` record by ID for full traceability: *"This finding was scored HIGH (72) based on: CVSS 7.3 (AV:N/AC:L), AI confidence 0.82 (two corroborating evidence items), Evidence Weight 4.0 (Semgrep + HTTP proof), Exploit Factor 0.80."*

---

## Anti-Gaming and Integrity Rules

1. **Evidence gate**: Findings with zero evidence weight are rejected before scoring. No exceptions.
2. **Confidence cap**: AI probability cannot exceed 0.80 with fewer than two corroborating evidence items. The cap is enforced by VulnScoringAgent, not by the LLM prompt.
3. **Inflation detection**: If mean AI confidence across all findings in a run exceeds 0.75, the `score_inflation_warning` event is emitted and logged in the report appendix.
4. **Immutability**: Score components are write-once. Retesting creates a new finding record and new score record. Old scores are preserved for comparison.
5. **CVSS grounding**: VulnScoringAgent validates that CVSS vector matches the evidence type (e.g., a static-only finding cannot have AV:N without justification).
6. **User annotation only**: Users can add notes to a finding but cannot change its VulnScore. They can trigger a retest, which produces a new score.
7. **Transparency**: Every score shown in the TUI and report has a `[Show breakdown]` option that displays the exact component values and rationale.
