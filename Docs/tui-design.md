# TUI Design Specification

## Framework Choice

Bug Hunter CLI uses **Textual** (Python) as its primary TUI framework — not just Rich. This is a deliberate choice.

| Library | Use Case |
|---|---|
| **Textual** | Full interactive TUI with reactive widgets, panels, modals, keyboard events, CSS-like styling |
| **Rich** | Inline styled output, progress bars, tables when running in non-TTY mode (CI, piped) |

**Why Textual over a plain Rich layout**:
- Textual gives proper panel layout with resizable columns
- Reactive state means the UI updates automatically when events arrive from agents
- CSS-like `.tcss` styling lets us define semantic colors for severity tiers in one place
- Keyboard bindings are first-class (pause, filter, inspect, approve gates)
- Modal dialogs for approval gates require widget lifecycle management that Rich cannot provide
- Textual's `ScrollView` handles live-streaming finding cards without manual cursor management

**Why not a web UI / browser-based**:
- Security tools should be terminal-native. No browser process, no localhost server, no external network calls for UI rendering.
- The TUI runs fully offline — critical for air-gapped or restricted environments.

---

## Layout Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔍 Bug Hunter CLI  │  run: abc123  │  elapsed: 00:04:12  │  model: gpt-4o  │  ← Header
├──────────────────────┬──────────────────────────────────┬────────────────────┤
│  PHASE TRACKER       │  LIVE FINDINGS STREAM             │  SCORE SUMMARY     │
│                      │                                   │                    │
│  [✓] Scope Load      │  ┌─────────────────────────────┐  │  Risk Overview:    │
│  [✓] Run Init        │  │ 🔴 CRITICAL  VulnScore: 94  │  │                    │
│  [✓] Recon + Index   │  │ SQL Injection — auth/views  │  │  🔴  1  CRITICAL   │
│  [↻] Test Planning   │  │ ████████████░░  94 / 100    │  │  🟠  2  HIGH       │
│  [ ] Static Audit    │  │ AI Conf: ██████████  0.91   │  │  🟡  3  MEDIUM     │
│  [ ] Dynamic Tests   │  │ Evidence: 3  Semgrep+HTTP   │  │  🔵  0  LOW        │
│  [ ] Scoring         │  └─────────────────────────────┘  │  ⚪  1  INFO       │
│  [ ] Report          │                                   │                    │
│                      │  ┌─────────────────────────────┐  │  Top Score:  94    │
│  ─────────────────   │  │ 🟠 HIGH      VulnScore: 72  │  │  Mean Score: 61.4  │
│  AGENT FEED          │  │ Missing Auth — /api/admin   │  │  Inflation:  OK    │
│                      │  │ ███████░░░░░  72 / 100      │  │                    │
│  [recon]   indexing  │  │ AI Conf: ████████░░  0.82   │  │  Tokens:  12,440   │
│            auth/...  │  │ Evidence: 2  Semgrep only   │  │  Cost: ~$0.04      │
│  [audit]   scanning  │  └─────────────────────────────┘  │                    │
│            views.py  │                                   │  [s] Score Detail  │
│  [score]   ranking   │  ┌─────────────────────────────┐  │  [f] Filter Tier   │
│            findings  │  │ 🟡 MEDIUM    VulnScore: 51  │  │                    │
│                      │  │ XSS — /search?q= reflection │  │                    │
│                      │  │ ██████░░░░░░  51 / 100      │  │                    │
│                      │  │ AI Conf: ██████░░░░  0.68   │  │                    │
│                      │  │ Evidence: 1  Semgrep match  │  │                    │
│                      │  └─────────────────────────────┘  │                    │
├──────────────────────┴──────────────────────────────────┴────────────────────┤
│  ▶ StaticAuditAgent → auth/views.py:142  │  Rate: OK  │  [p]ause  [q]uit     │  ← Footer
└─────────────────────────────────────────────────────────────────────────────┘
```

**Column widths**: Left panel = 28 columns, Right panel = 22 columns, Main panel = remaining (flexible).

---

## Panel Descriptions

### Header Bar
- **Widget**: Custom `Header` extending `Textual.widgets.Header`
- **Content**: Tool name + ASCII logo, run ID (first 8 chars), elapsed time (live counter), active provider + model name
- **Update frequency**: Elapsed time updates every second via a `set_interval` reactive
- **Height**: 1 line

### Left Panel — Phase Tracker

**Widget**: `PhaseTrackerWidget(Static)` with reactive `current_phase: str`

Shows the 8-phase pipeline with status icons:
```
[✓] = done        (green)
[↻] = running     (yellow, animated spinner)
[ ] = pending     (grey)
[!] = error       (red)
```

Phases in order:
1. Scope Load
2. Run Init
3. Recon + Index
4. Test Planning
5. Static Audit
6. Dynamic Tests
7. Scoring
8. Report

Each phase transitions automatically as `phase_started` and `phase_completed` events are received from the event bus.

### Left Panel — Agent Feed

**Widget**: `AgentFeedWidget(ScrollView)` — auto-scrolls to latest entry

Shows a live log of what each agent is doing. Format:
```
[agent_name]  short description of current action
              file or target (if applicable)
```

Rules:
- **Never shows chain-of-thought reasoning**
- Shows: current file being scanned, current test being run, current finding being scored, current target URL
- Maximum 100 entries before oldest are dropped (ring buffer)
- Color: agent name in dim cyan, action in white, file path in dim white

### Main Panel — Live Findings Stream

**Widget**: `FindingsStreamWidget(ScrollView)` — new findings prepend to top (highest scoring first)

Each finding is a `FindingCard(Widget)` with reactive `vuln_score`, `ai_prob`, `evidence_count`.

**Finding Card Layout**:
```
┌─────────────────────────────────────────────┐
│ 🔴 CRITICAL [94]  SQL Injection              │  ← Title line (color = risk tier)
│ auth/views.py:142 • POST /api/login          │  ← Location line (dim)
│                                              │
│ VulnScore  ████████████░░  94 / 100          │  ← Progress bar (colored)
│ AI Conf    ██████████░░░░  0.91 (91%)        │  ← Probability bar (animated)
│ Evidence   3 items  [Semgrep ✓] [HTTP ✓]    │  ← Evidence badges
└─────────────────────────────────────────────┘
```

**Re-ranking**: When a new `finding_scored` event arrives, the list re-sorts in descending VulnScore order with a smooth scroll-to-top for the new card.

**Color Scheme**:
| Tier | Border Color | Score Bar | Badge |
|---|---|---|---|
| CRITICAL | `bright_red` | `bright_red` | 🔴 |
| HIGH | `dark_orange` | `dark_orange` | 🟠 |
| MEDIUM | `yellow3` | `yellow3` | 🟡 |
| LOW | `steel_blue` | `steel_blue` | 🔵 |
| INFORMATIONAL | `grey50` | `grey50` | ⚪ |

### Right Panel — Score Summary

**Widget**: `ScoreSummaryWidget(Static)` with reactive counters per tier

Shows:
- Tier counts: `🔴 1 CRITICAL`, `🟠 2 HIGH`, etc.
- Top score (highest VulnScore in run)
- Mean score (mean of all scored findings)
- Inflation warning (shown if mean AI confidence > 0.75 across run)
- Token usage and estimated cost (from ContextManagerAgent events)

Keyboard hints at bottom: `[s] Score Detail`, `[f] Filter Tier`

### Footer Bar

**Widget**: Custom `Footer` extending `Textual.widgets.Footer`

Content:
- `▶ AgentName → current_target` (left)
- Rate limit state: `Rate: OK` or `Rate: Paused 3s` (center)
- Keyboard hint strip: `[p]ause  [q]uit  [e]xport  [?]help` (right)

---

## Scoring Display — The AI Reasoning Panel

The scoring display is the most critical UI element for building trust in the AI's reasoning.

### Probability Bar Animation

When VulnScoringAgent emits a `finding_scored` event:

1. A new `FindingCard` is mounted at the top of the stream with all bars at 0.
2. The VulnScore bar fills from left to right over **0.6 seconds** using a CSS transition.
3. The AI Confidence bar fills from left to right over **0.8 seconds** (slightly delayed).
4. The evidence badges pop in one by one over 0.4 seconds.

This animation sequence communicates: *"The tool has done real analysis and is now summarizing its confidence."* It avoids the feeling of instant, uncalibrated AI output.

### Score Breakdown Modal

Pressing `s` with a finding selected opens a modal:

```
┌────────────────────────────────────────────────────┐
│  SCORE BREAKDOWN — SQL Injection (auth/views.py)   │
│                                                    │
│  VulnScore:           94 / 100   🔴 CRITICAL      │
│                                                    │
│  Component              Value    Weight   Points   │
│  CVSS Base (8.1)        8.1      35%      2.84    │
│  AI Confidence (0.91)   0.91     25%      2.27    │
│  Evidence Weight (4.5)  4.5      20%      1.80    │
│  Exploit Factor (0.80)  0.80     12%      0.96    │
│  Remed Penalty          -0.05    8%      -0.38    │
│                                         ──────    │
│  Raw:  7.49  →  Normalized:  81.4  →  Capped: 94  │
│                                                    │
│  CVSS Vector: AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N │
│  Evidence:    Semgrep rule python.django.sqli,     │
│               HTTP POST /api/login with 500 resp.  │
│  Confidence:  2 corroborating items → cap lifted   │
│                                                    │
│  [Enter] Close   [r] Retest   [e] Export finding   │
└────────────────────────────────────────────────────┘
```

---

## Phase Tracker Widget

The phase tracker shows the full pipeline state at a glance:

```
PHASE TRACKER
─────────────
[✓] Scope Load      0.2s
[✓] Run Init        0.1s
[✓] Recon + Index   1m 34s
[↻] Test Planning   ···
[ ] Static Audit
[ ] Dynamic Tests
[ ] Scoring
[ ] Report
```

State transitions are driven by `phase_started` and `phase_completed` events from the LangGraph state machine. The running phase shows an animated spinner character cycling through `⣾⣽⣻⢿⡿⣟⣯⣷`.

Each completed phase shows its duration for performance transparency.

---

## Approval Gate Modals

When the agent pipeline reaches a checkpoint requiring user approval, a Textual `ModalScreen` is pushed on top of the main layout.

### Safe-Active Approval

```
┌───────────────────────────────────────────────┐
│  ⚠️  APPROVAL REQUIRED                        │
│                                               │
│  Bug Hunter CLI wants to run safe-active      │
│  network tests against:                       │
│                                               │
│    http://localhost:3000                      │
│                                               │
│  These tests send scoped HTTP requests.       │
│  No destructive payloads will be used.        │
│  Rate limit: 60 req/min.                      │
│                                               │
│  [Y] Approve   [N] Deny   [V] View Scope      │
└───────────────────────────────────────────────┘
```

### Lab Validation Approval

```
┌───────────────────────────────────────────────┐
│  🔬 LAB VALIDATION REQUIRED                   │
│                                               │
│  This test requires lab-validation mode.      │
│  Target is marked as an owned lab instance.   │
│                                               │
│  Test: Controlled archive expansion limit     │
│  Risk: Resource spike on target (isolated)   │
│                                               │
│  [Y] Approve   [N] Skip   [V] View Test Plan  │
└───────────────────────────────────────────────┘
```

### Race Condition Approval

```
┌───────────────────────────────────────────────┐
│  🏁 RACE CONDITION TEST APPROVAL              │
│                                               │
│  Sending 5 concurrent requests to:            │
│    POST /api/coupon/redeem                   │
│  Using test account: test_user_01             │
│  Concurrency cap: 5 (hard limit)              │
│                                               │
│  [Y] Approve   [N] Skip                       │
└───────────────────────────────────────────────┘
```

All modals block the agent pipeline until resolved. The footer shows `⏸ Waiting for approval...` during this time.

---

## Heartbeat Events and Waiting States

Long-running operations (model calls, large file scans) must never make the TUI appear frozen.

### Model Waiting State

When an LLM call is in progress, the Agent Feed shows:

```
[provider]  ⣷ Waiting for model response...  (00:12)
```

The spinner animates every 0.1 seconds. The elapsed counter updates every second. The footer shows `⏳ Model call in progress`.

### Rate Limited State

When `rate_limited` event arrives:

```
[http]  ⏱ Rate limited — retry in 3s
```

The footer shows `Rate: Paused 3s` with a countdown that ticks down in real time. When the wait ends, the status returns to `Rate: OK`.

### Still Running Pulse

For operations where no intermediate output is expected (e.g., Semgrep scanning a large codebase), a `still_running` event is emitted every 15 seconds:

```
[audit]  ↻ Still scanning — 247 files processed, 3 findings so far
```

---

## Keyboard Controls

| Key | Action |
|---|---|
| `q` | Quit — prompts "Save partial results? [Y/N]" |
| `p` | Pause current agent (saves state) |
| `r` | Resume paused agent |
| `e` | Export report now (generates partial report) |
| `i` | Inspect artifacts — opens file picker for run directory |
| `f` | Filter findings — opens tier filter (All / CRITICAL+HIGH / MEDIUM+ / etc.) |
| `s` | Score detail for selected finding |
| `a` | Show pending approvals |
| `↑↓` | Navigate finding list |
| `Enter` | Expand/collapse finding card |
| `?` | Help overlay |
| `Ctrl+C` | Same as `q` — prompts save |

---

## Interruption Handling

When the user presses `q` or `Ctrl+C` during a run:

1. A modal appears: *"Run in progress. Save partial results before exiting?"*
2. If `[Y]`: CliUiAgent signals the LangGraph graph to stop after the current node, then calls `ArtifactWriter` to write a partial `test-results.md` and a partial `bug-report.md` marked as `[INCOMPLETE]`.
3. If `[N]`: The process exits immediately. SQLite preserves whatever was committed before exit.
4. Partial runs can be resumed with `bughunter scan --resume <run_id>`.

---

## Textual App Structure

```
BugHunterApp (App)
├── BugHunterHeader (Header)
│   ├── RunIdLabel (Label)
│   ├── ElapsedTimer (Label) — reactive timer
│   └── ModelLabel (Label)
│
├── Body (Horizontal)
│   ├── LeftPanel (Vertical, width=28)
│   │   ├── PhaseTrackerWidget (Widget)
│   │   │   └── PhaseRow × 8 (Static)
│   │   └── AgentFeedWidget (ScrollView)
│   │       └── AgentLogEntry × n (Static)
│   │
│   ├── MainPanel (Vertical, width=1fr)
│   │   └── FindingsStreamWidget (ScrollView)
│   │       └── FindingCard × n (Widget)
│   │           ├── TitleLine (Static)
│   │           ├── LocationLine (Static)
│   │           ├── VulnScoreBar (ProgressBar)
│   │           ├── AIProbBar (ProgressBar)
│   │           └── EvidenceBadges (Horizontal)
│   │
│   └── RightPanel (Vertical, width=22)
│       └── ScoreSummaryWidget (Widget)
│           ├── TierCountRow × 5 (Static)
│           ├── StatsBlock (Static)
│           └── TokenCostBlock (Static)
│
├── BugHunterFooter (Footer)
│   ├── CurrentOpLabel (Label)
│   ├── RateStatusLabel (Label)
│   └── KeyHintStrip (Static)
│
└── (Modal screens, pushed on demand)
    ├── ApprovalModal (ModalScreen)
    ├── ScoreBreakdownModal (ModalScreen)
    ├── HelpModal (ModalScreen)
    └── InterruptModal (ModalScreen)
```

### Reactive Data Flow

```
EventBus (internal)
    │
    ├─→ phase_started / phase_completed  →  PhaseTrackerWidget.update_phase()
    ├─→ agent_action                     →  AgentFeedWidget.append_entry()
    ├─→ finding_scored                   →  FindingsStreamWidget.add_card()
    │                                       ScoreSummaryWidget.increment_tier()
    ├─→ model_waiting                    →  AgentFeedWidget.show_spinner()
    │                                       FooterLabel.set_status()
    ├─→ rate_limited                     →  FooterLabel.start_countdown()
    ├─→ approval_required               →  app.push_screen(ApprovalModal)
    └─→ report_written                  →  FooterLabel.show_export_path()
```

All reactive updates are non-blocking. The event bus uses `asyncio.Queue` internally and Textual's `call_from_thread` for cross-thread widget updates.

---

## Theme and Styling (`bughunter.tcss`)

```css
/* Base theme */
Screen {
    background: #0d1117;
    color: #e6edf3;
}

/* Panels */
LeftPanel {
    border-right: solid #30363d;
    padding: 0 1;
}

RightPanel {
    border-left: solid #30363d;
    padding: 0 1;
}

/* Phase tracker */
.phase-done { color: #3fb950; }         /* green */
.phase-running { color: #d29922; }      /* yellow */
.phase-pending { color: #484f58; }      /* grey */
.phase-error { color: #f85149; }        /* red */

/* Finding cards */
FindingCard {
    border: solid #30363d;
    margin: 0 0 1 0;
    padding: 0 1;
}

.tier-critical { border: solid #f85149; }
.tier-high     { border: solid #d97706; }
.tier-medium   { border: solid #d29922; }
.tier-low      { border: solid #388bfd; }
.tier-info     { border: solid #484f58; }

/* Score bars */
.bar-critical { color: #f85149; }
.bar-high     { color: #d97706; }
.bar-medium   { color: #d29922; }
.bar-low      { color: #388bfd; }
.bar-info     { color: #484f58; }

/* Monospace for paths and code */
.code-text {
    font-family: monospace;
    color: #8b949e;
}

/* Agent feed */
.agent-name { color: #58a6ff; }
.agent-action { color: #e6edf3; }
```

---

## Non-TUI Fallback (CI Mode)

When stdout is not a TTY (detected via `sys.stdout.isatty()`), Bug Hunter CLI falls back to Rich structured logging:

```
[14:32:01] INFO     phase_started: recon
[14:32:01] INFO     recon: building repository manifest
[14:32:15] INFO     recon: index.md written (148 entries)
[14:32:15] INFO     phase_completed: recon (14.2s)
[14:32:15] INFO     phase_started: static_audit
[14:32:22] WARNING  finding: SQL Injection in auth/views.py:142 [score=94, CRITICAL]
[14:32:35] INFO     phase_completed: static_audit (20.1s)
[14:32:35] INFO     report written: .bughunter/runs/abc123/bug-report.md
```

**JSON event stream** (for machine consumption via `--json-events`):

```json
{"ts": "2026-06-25T14:32:22Z", "type": "finding_scored", "run_id": "abc123", "finding_id": "f001", "title": "SQL Injection", "vuln_score": 94, "risk_tier": "CRITICAL", "ai_prob": 0.91}
```

This allows CI pipelines to parse findings, set exit codes based on CRITICAL/HIGH counts, and post results to GitHub PR comments or issue trackers.
