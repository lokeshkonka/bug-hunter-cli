# VulnScoringAgent

## Identity

**Name**: VulnScoringAgent  
**Role**: Vulnerability scoring, risk tier assignment, and finding prioritization  
**Phase**: Runs after EvidenceAgent, before FixAgent and ReportAgent  
**LangGraph node**: `score_findings`

---

## Purpose

VulnScoringAgent receives normalized findings from EvidenceAgent and assigns each one a composite VulnScore (0–100). It is the primary source of risk prioritization in Bug Hunter CLI.

Its job is to answer: *"Given everything we know about this finding — the CVSS characteristics, how confident the AI is, how much evidence we have, and how exploitable this is — what is the real risk level?"*

The agent does not discover new vulnerabilities. It only evaluates findings that already have deterministic evidence attached.

See `Docs/scoring-system.md` for the full scoring formula and component weights.

---

## Inputs

- Normalized finding from EvidenceAgent (with all evidence records attached)
- Index entry metadata (for CVSS vector context and exploitability)
- Historical false-positive rates per scanner + category (from SQLite)
- Run configuration (scan mode, allowed confidence caps)

---

## Outputs

- `finding_scored` event emitted to CliUiAgent (TUI update)
- Score record written to `score_components` SQLite table
- Finding updated with `vuln_score`, `risk_tier`, `score_breakdown`
- Ranked finding list passed to FixAgent and ReportAgent

---

## Scoring Process

1. **Evidence gate**: Reject findings with zero evidence weight. Emit `finding_rejected` event. Do not pass to report.
2. **Evidence weight computation**: Aggregate evidence items from EvidenceAgent. Apply the evidence scoring table from `Docs/scoring-system.md`.
3. **CVSS vector proposal**: Send a structured prompt to the LLM provider with the evidence packet. Parse the response as a typed `CvssVector` model. Validate that the vector is consistent with the evidence type (e.g., static-only cannot claim AV:N without justification).
4. **AI confidence calibration**: Apply calibration rules based on category, evidence count, and historical scanner accuracy. Cap confidence as specified in `Docs/scoring-system.md`.
5. **Exploitability factor**: Compute from index entry metadata, finding category, and CVSS vector components.
6. **Remediation penalty**: Request from FixAgent (blocking call within the graph node).
7. **VulnScore computation**: Apply the composite formula. Normalize to 0–100.
8. **Inflation check**: After each scoring, update the running mean confidence for the run. If mean > 0.75, emit `score_inflation_warning`.
9. **Write to SQLite**: Store all component values and rationale to `score_components`.
10. **Emit event**: Emit `finding_scored` with `vuln_score`, `risk_tier`, `ai_prob`, `evidence_count` for TUI update.

---

## AI Role

The AI (LLM provider) is used for:

- Proposing the CVSS vector based on the evidence packet (structured output)
- Calibrated confidence probability output (structured float field)
- Generating a human-readable rationale string for each score component

The AI is NOT used for:

- Computing the final VulnScore (that is deterministic Python code)
- Assigning risk tiers (that is a threshold lookup)
- Validating evidence existence (that is EvidenceAgent's job)

All AI calls use structured output parsing. No raw text parsing of score components.

---

## Anti-Inflation Rules

- AI confidence cannot exceed 0.80 with fewer than 2 corroborating evidence items. This is enforced in Python, not by prompt.
- If the proposed CVSS vector is inconsistent with evidence type, the agent downgrades AV or increases AC and logs the adjustment.
- Score inflation detection: if mean AI confidence across all findings in the run exceeds 0.75, a `score_inflation_warning` event is emitted.

---

## Failure Handling

- If the LLM provider is unavailable, VulnScoringAgent falls back to a deterministic scoring mode:
  - CVSS vector is estimated from category + index tags
  - AI confidence defaults to the category default range (lower bound)
  - A `fallback_scoring` flag is set on the finding
- Partial runs preserve whatever findings were scored before the failure.

---

## SQLite Schema Reference

```sql
CREATE TABLE score_components (
    id               TEXT PRIMARY KEY,
    finding_id       TEXT NOT NULL REFERENCES findings(id),
    run_id           TEXT NOT NULL,
    cvss_score       REAL NOT NULL,
    cvss_vector      TEXT NOT NULL,
    cvss_rationale   TEXT NOT NULL,
    ai_prob          REAL NOT NULL,
    ai_prob_rationale TEXT NOT NULL,
    evidence_weight  REAL NOT NULL,
    evidence_items   TEXT NOT NULL,  -- JSON array of evidence IDs
    exploit_factor   REAL NOT NULL,
    exploit_rationale TEXT NOT NULL,
    remed_penalty    REAL NOT NULL,
    remed_rationale  TEXT NOT NULL,
    vuln_score       REAL NOT NULL,
    risk_tier        TEXT NOT NULL,
    computed_at      TEXT NOT NULL,
    inflation_flag   INTEGER DEFAULT 0,
    fallback_scoring INTEGER DEFAULT 0
);
```

---

## Safety Rules

- VulnScoringAgent never modifies evidence records. It reads them.
- It never creates new findings. It only scores existing ones.
- Score records are immutable after creation. Retests create new records.
- It never bypasses the evidence gate. Zero evidence = rejection, always.
