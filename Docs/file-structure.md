# Bug Hunter CLI — System Design & File Structure

> **Design Principles Applied**: Single Responsibility (SRP), Open/Closed (OCP),
> Liskov Substitution (LSP), Interface Segregation (ISP), Dependency Inversion (DIP),
> plus Separation of Concerns, Law of Demeter, and Hexagonal Architecture.

---

## Architecture Overview

Bug Hunter CLI is built as a **Hexagonal (Ports & Adapters) Architecture** layered
over a **LangGraph agent pipeline**. The system is split into three rings:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OUTER RING — Adapters                        │
│  CLI (Typer)   TUI (Textual)   Providers (OpenAI/Gemini/Groq)   CI mode  │
├─────────────────────────────────────────────────────────────────────┤
│                      MIDDLE RING — Application                      │
│   Agents (LangGraph nodes)   Orchestration Graph   Event Bus        │
├─────────────────────────────────────────────────────────────────────┤
│                       INNER RING — Domain                           │
│  Scoring Engine   Safety Policy   Evidence Models   Findings Models  │
└─────────────────────────────────────────────────────────────────────┘
```

**Rules between rings**:
- Inner Ring has **zero dependencies** on Outer or Middle rings.
- Middle Ring depends only on Inner Ring interfaces (ports), never on concrete adapters.
- Outer Ring adapters plug into Middle Ring ports. They can be swapped without touching domain logic.
- All dependencies point **inward**.

---

## Design Principle Map

| Layer | Package | Primary Principle | Notes |
|---|---|---|---|
| CLI entrypoint | `bughunter/cli.py` | SRP | One file, one job: parse args and dispatch. No business logic. |
| Agent nodes | `bughunter/agents/` | SRP + OCP | Each agent has one job. New agents extend `BaseAgent`, never modify it. |
| Orchestration | `bughunter/graph/` | SRP | Graph wiring is separate from agent logic. |
| Safety | `bughunter/core/safety/` | SRP + DIP | Policy engine accepts a `ScopePort` interface, not a concrete scope object. |
| HTTP | `bughunter/core/http/` | SRP | Scope enforcement is a decorator/wrapper, not embedded in agent code. |
| Scanners | `bughunter/scanners/` | OCP + LSP | New scanners implement `BaseScanner` and slot in without changing existing code. |
| Scoring | `bughunter/scoring/` | SRP | Five components, five separate modules. Composite formula is pure Python, not LLM. |
| Providers | `bughunter/providers/` | DIP + LSP | Agents depend on `ProviderPort` ABC. OpenAI, Gemini, and Groq/Grok are interchangeable. |
| Storage | `bughunter/storage/` | ISP | Four focused store classes, not one god-object repository. |
| Reports | `bughunter/reports/` | OCP | New export formats (SARIF, JSON, PDF) are new classes, not conditionals in one file. |
| TUI | `bughunter/tui/` | SRP | Each widget owns one piece of data. App wires them together. |
| Models | `bughunter/models/` | SRP | Domain models live here, separate from storage schemas and API contracts. |

---

## Dependency Flow (No Circular Dependencies)

```
cli.py
  └─→ graph/ (orchestration)
        └─→ agents/ (LangGraph nodes)
              ├─→ models/ (domain data structures)     ← no external deps
              ├─→ core/safety/ (policy engine)          ← no agent deps
              ├─→ core/http/ (scoped HTTP)              ← no agent deps
              ├─→ core/events/ (event bus)              ← no agent deps
              ├─→ scanners/ (deterministic tools)       ← no agent/LLM deps
              ├─→ scoring/ (composite formula)          ← no agent/LLM deps
              ├─→ providers/ (LLM adapters)             ← no agent deps
              ├─→ storage/ (persistence)                ← no agent deps
              └─→ reports/ (exporters)                  ← no agent deps

tui/
  └─→ core/events/ (subscribes to event bus)
  └─→ models/ (reads typed events/findings)
  (never imports from agents/ directly)
```

---

## Complete Project Layout

```
bug-hunter-cli/
│
├── pyproject.toml                      # Build config, CLI entry, dependencies, tool config
├── uv.lock                             # Pinned lockfile (committed to git)
├── .python-version                     # 3.12 (pinned for reproducibility)
├── .gitignore
├── .ruff.toml                          # Linting rules (separate from pyproject for readability)
├── .mypy.ini                           # Strict type checking config
├── README.md                           # Quickstart, install, usage, badges, screenshot
├── CHANGELOG.md                        # Semantic versioning changelog
├── SECURITY.md                         # Vulnerability disclosure policy for the tool itself
│
│   ── Docs ──────────────────────────────────────────────────────────────────
│
├── Docs/
│   ├── Overall-plan.md                 # Product vision, agent architecture, phases
│   ├── scoring-system.md               # VulnScore formula, components, anti-gaming rules
│   ├── tui-design.md                   # Textual TUI layout, wireframes, widgets
│   ├── strict-ai-safety.md             # AI safety contract, PromptGuardAgent rules
│   ├── test-library.md                 # Reusable test definitions, Semgrep rule refs
│   ├── artifact-workflow.md            # index.md → testN.md → test-results.md → bug-report.md
│   ├── robustness-checklist.md         # Full production readiness checklist
│   ├── phase1.md → phase5.md           # Phased implementation plans
│   │
│   ├── agents/                         # One doc per agent (matches one file per agent in code)
│   │   ├── planner_agent.md
│   │   ├── recon_agent.md
│   │   ├── static_audit_agent.md
│   │   ├── dynamic_test_agent.md
│   │   ├── evidence_agent.md
│   │   ├── vuln_scoring_agent.md       # NEW
│   │   ├── fix_agent.md
│   │   ├── report_agent.md
│   │   ├── retest_agent.md             # NEW
│   │   ├── context_manager_agent.md    # NEW
│   │   ├── prompt_guard_agent.md       # NEW
│   │   └── cli_ui_agent.md
│   │
│   └── templates/                      # Artifact templates (used by ArtifactWriter)
│       ├── bug-report-template.md
│       ├── index-template.md
│       ├── test-plan-template.md
│       ├── test-results-template.md
│       └── scope-template.yml          # Full scope file example with all options
│
│   ── Source ────────────────────────────────────────────────────────────────
│
├── bughunter/
│   │
│   ├── __init__.py                     # Package version, public re-exports only
│   │
│   ├── cli.py                          # [SRP] Typer app — parses args, calls graph, returns exit code
│   │                                   # No business logic here. Pure dispatch.
│   │
│   │   ── models ── (Inner Ring — no external deps) ─────────────────────────
│   │
│   ├── models/
│   │   ├── __init__.py                 # Re-exports all public models
│   │   ├── run.py                      # [SRP] Run, RunStatus, RunSummary
│   │   ├── scope.py                    # [SRP] Scope, Target, ScanMode, CostBudget
│   │   ├── event.py                    # [SRP] BugHunterEvent, EventType (dataclass, frozen)
│   │   ├── evidence.py                 # [SRP] Evidence, EvidenceType, EvidenceWeight
│   │   ├── finding.py                  # [SRP] Finding, FindingStatus, Confidence, Severity
│   │   ├── score.py                    # [SRP] ScoreComponents, VulnScore, RiskTier
│   │   ├── test_plan.py                # [SRP] TestPlan, SafetyClass, TestCategory
│   │   ├── test_result.py              # [SRP] TestResult, TestStatus
│   │   ├── report.py                   # [SRP] Report, ReportFormat, ReportSection
│   │   ├── policy.py                   # [SRP] PolicyDecision, PolicyViolation, PolicyAction
│   │   └── provider.py                 # [SRP] ProviderConfig, UsageRecord, CvssVector
│   │                                   #
│   │                                   # ► All models are Pydantic v2, frozen=True (immutable)
│   │                                   # ► No circular imports between model files
│   │                                   # ► No imports from agents/, storage/, or providers/
│   │
│   │   ── core ── (Infrastructure Ports — Middle Ring) ──────────────────────
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   │
│   │   ├── safety/                     # [SRP] Everything safety-related, grouped together
│   │   │   ├── __init__.py
│   │   │   ├── engine.py               # [SRP] SafetyPolicyEngine — single source of truth
│   │   │   │                           #   .check(action) → PolicyDecision
│   │   │   │                           #   .block(action) → PolicyViolation
│   │   │   │                           #   Depends on: models/policy.py, models/scope.py
│   │   │   ├── scope_validator.py      # [SRP] Validates bughunter-scope.yml structure
│   │   │   │                           #   Separate from engine: validation ≠ enforcement
│   │   │   ├── mode_classifier.py      # [SRP] Classifies test as passive/safe-active/lab/blocked
│   │   │   │                           #   Pure function: (test_category, scope) → SafetyClass
│   │   │   └── rate_limiter.py         # [SRP] Token-bucket rate limiter per hostname
│   │   │                               #   No HTTP logic. Just rate state.
│   │   │
│   │   ├── http/                       # [SRP] All HTTP concerns, isolated from agents
│   │   │   ├── __init__.py
│   │   │   ├── scoped_client.py        # [SRP] ScopedHttpClient — wraps httpx, enforces scope
│   │   │   │                           #   .get() / .post() → checks scope → sends or rejects
│   │   │   │                           #   Uses: safety/engine.py, safety/rate_limiter.py
│   │   │   └── request_evidence.py     # [SRP] Captures request+response as Evidence record
│   │   │                               #   Separate from client: capture ≠ sending
│   │   │
│   │   ├── events/                     # [SRP] Event system, used by all layers
│   │   │   ├── __init__.py
│   │   │   ├── bus.py                  # [SRP] AsyncEventBus — asyncio.Queue, publish/subscribe
│   │   │   ├── types.py                # [SRP] All EventType literals in one place
│   │   │   └── emitter.py              # [SRP] AgentEventEmitter mixin — emit() helper
│   │   │                               #   Agents compose this in, don't inherit EventBus
│   │   │
│   │   ├── secrets/                    # [SRP] Secret handling — completely isolated
│   │   │   ├── __init__.py
│   │   │   ├── redactor.py             # [SRP] SecretRedactor — masks before storage/LLM
│   │   │   │                           #   Input: raw text → Output: masked text + metadata
│   │   │   └── patterns.py             # [SRP] All regex patterns for secret detection
│   │   │                               #   Separate from redactor: patterns ≠ redaction logic
│   │   │
│   │   └── artifacts/                  # [SRP] File artifact writing — isolated I/O
│   │       ├── __init__.py
│   │       ├── writer.py               # [SRP] ArtifactWriter — writes index.md, testN.md, etc.
│   │       │                           #   Knows paths, handles atomic writes, no domain logic
│   │       └── paths.py                # [SRP] RunPaths — all .bughunter/runs/<id>/ paths
│   │                                   #   One source of truth for all artifact file paths
│   │
│   │   ── graph ── (Orchestration — Middle Ring) ──────────────────────────────
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py                    # [SRP] BugHunterState TypedDict — graph's shared memory
│   │   │                               #   Only graph state here, not domain models
│   │   ├── builder.py                  # [SRP] build_graph() — wires nodes + edges, returns graph
│   │   │                               #   Graph topology is here. Node logic is in agents/.
│   │   ├── checkpointer.py             # [SRP] BugHunterCheckpointer — SQLite-backed LangGraph
│   │   │                               #   resume support. Separate from RunStore.
│   │   └── conditions.py               # [SRP] Conditional edge functions (pure predicates)
│   │                                   #   e.g., has_dynamic_targets(), approved_active_scan()
│   │
│   │   ── agents ── (Application Layer — Middle Ring) ─────────────────────────
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                     # [SRP] BaseAgent ABC
│   │   │                               #   run(state) → state  (one abstract method)
│   │   │                               #   Composes: EventEmitter, NO inheritance of storage
│   │   │
│   │   │   ── PLANNING AGENTS ──────────────────────────────────────────────
│   │   │
│   │   ├── planner/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # [SRP] PlannerAgent — scan plan creation
│   │   │   │                           #   Reads: scope, index entries
│   │   │   │                           #   Writes: TestPlan records, testN.md artifacts
│   │   │   ├── test_selector.py        # [SRP] TestSelector — selects tests from TestRegistry
│   │   │   │                           #   Pure function: (index_tags, scan_mode) → [TestDef]
│   │   │   └── plan_writer.py          # [SRP] PlanWriter — renders testN.md from TestPlan
│   │   │                               #   Separate from agent: rendering ≠ planning logic
│   │   │
│   │   │   ── RECON AGENTS ─────────────────────────────────────────────────
│   │   │
│   │   ├── recon/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # [SRP] ReconAgent — coordinates manifest + index build
│   │   │   ├── manifest_builder.py     # [SRP] ManifestBuilder — walks repo, builds file list
│   │   │   │                           #   Pure I/O: reads filesystem, returns RepositoryManifest
│   │   │   ├── relevance_scorer.py     # [SRP] RelevanceScorer — scores files by security value
│   │   │   │                           #   Pure function: (file_path, content_hints) → float
│   │   │   ├── language_detector.py    # [SRP] LanguageDetector — detects stack from manifests
│   │   │   │                           #   Pure function: (file_list) → LanguageStack
│   │   │   └── index_writer.py         # [SRP] IndexWriter — renders index.md from index entries
│   │   │                               #   Rendering logic only. Uses ArtifactWriter for I/O.
│   │   │
│   │   │   ── AUDIT AGENTS ─────────────────────────────────────────────────
│   │   │
│   │   ├── static_audit/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # [SRP] StaticAuditAgent — coordinates static analysis
│   │   │   ├── audit_packet_builder.py # [SRP] AuditPacketBuilder — assembles snippet+index+semgrep
│   │   │   │                           #   Calls ContextManagerAgent to enforce token limits
│   │   │   └── false_positive_filter.py # [SRP] FalsePositiveFilter — removes known safe patterns
│   │   │                               #   Pure function: (semgrep_match, context) → bool
│   │   │
│   │   ├── dynamic_test/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # [SRP] DynamicTestAgent — HTTP test execution coordinator
│   │   │   ├── test_executor.py        # [SRP] TestExecutor — executes one testN.md plan
│   │   │   │                           #   Reads plan → runs tools → appends test-results.md
│   │   │   └── results_writer.py       # [SRP] ResultsWriter — appends to test-results.md
│   │   │                               #   Append-only. Knows format, not test logic.
│   │   │
│   │   │   ── EVIDENCE AGENTS ──────────────────────────────────────────────
│   │   │
│   │   ├── evidence/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # [SRP] EvidenceAgent — evidence pipeline coordinator
│   │   │   ├── normalizer.py           # [SRP] EvidenceNormalizer — canonical evidence format
│   │   │   │                           #   Pure transform: raw scanner output → Evidence model
│   │   │   ├── deduplicator.py         # [SRP] EvidenceDeduplicator — merges duplicate evidence
│   │   │   │                           #   Pure function: [Evidence] → [Evidence] (deduplicated)
│   │   │   └── weight_calculator.py    # [SRP] EvidenceWeightCalculator — scores evidence quality
│   │   │                               #   Pure function: [Evidence] → float (0-5)
│   │   │
│   │   │   ── SCORING AGENTS ──────────────────────────────────────────────
│   │   │
│   │   ├── vuln_scoring/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # [SRP] VulnScoringAgent — orchestrates scoring pipeline
│   │   │   │                           #   Calls scoring/ modules. Does NOT compute scores itself.
│   │   │   └── inflation_detector.py   # [SRP] InflationDetector — detects mean confidence > 0.75
│   │   │                               #   Pure function: [ScoredFinding] → InflationReport
│   │   │
│   │   │   ── FIX AGENTS ──────────────────────────────────────────────────
│   │   │
│   │   ├── fix/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # [SRP] FixAgent — coordinates remediation generation
│   │   │   ├── patch_formatter.py      # [SRP] PatchFormatter — renders diff-style patch output
│   │   │   │                           #   Pure rendering: Finding + snippet → patch string
│   │   │   └── complexity_assessor.py  # [SRP] ComplexityAssessor — assesses remediation difficulty
│   │   │                               #   Returns RemediationComplexity for scoring penalty
│   │   │
│   │   │   ── REPORT AGENTS ──────────────────────────────────────────────
│   │   │
│   │   ├── report/
│   │   │   ├── __init__.py
│   │   │   └── agent.py                # [SRP] ReportAgent — calls reports/ exporters
│   │   │                               #   Reads from storage, delegates to reports/ for rendering
│   │   │                               #   Does not contain rendering logic itself
│   │   │
│   │   │   ── RETEST AGENTS ──────────────────────────────────────────────
│   │   │
│   │   ├── retest/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # [SRP] RetestAgent — orchestrates retest workflow
│   │   │   ├── evidence_comparator.py  # [SRP] EvidenceComparator — old vs new evidence diff
│   │   │   │                           #   Pure function: (old_ev, new_ev) → FindingStatus
│   │   │   └── status_updater.py       # [SRP] StatusUpdater — updates finding lifecycle state
│   │   │                               #   Wraps storage call: write-only concern
│   │   │
│   │   │   ── SUPPORT AGENTS ──────────────────────────────────────────────
│   │   │
│   │   ├── context_manager/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # [SRP] ContextManagerAgent — budget + snippet coordinator
│   │   │   ├── snippet_selector.py     # [SRP] SnippetSelector — tag-ranked snippet selection
│   │   │   │                           #   Pure function: (index_entries, tags, max_tokens) → [Snippet]
│   │   │   ├── token_budget.py         # [SRP] TokenBudget — tracks and enforces token limits
│   │   │   │                           #   Stateful: tracks usage, emits budget_warning events
│   │   │   └── snippet_cache.py        # [SRP] SnippetCache — in-memory + SQLite cache
│   │   │                               #   Cache only: no selection logic
│   │   │
│   │   ├── prompt_guard/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # [SRP] PromptGuardAgent — content validation coordinator
│   │   │   ├── injection_classifier.py # [SRP] InjectionClassifier — multi-layer detection
│   │   │   │                           #   Pure function: (text, sensitivity) → InjectionResult
│   │   │   └── content_wrapper.py      # [SRP] ContentWrapper — wraps content as evidence blocks
│   │   │                               #   Pure transform: raw text → wrapped evidence string
│   │   │
│   │   └── cli_ui/
│   │       ├── __init__.py
│   │       └── agent.py                # [SRP] CliUiAgent — translates events to TUI updates
│   │                                   #   Subscribes to EventBus, calls tui/ widget methods
│   │                                   #   Does NOT contain any widget or rendering logic
│   │
│   │   ── scanners ── (Tool Adapters — Outer Ring) ──────────────────────────
│   │
│   ├── scanners/
│   │   ├── __init__.py
│   │   ├── base.py                     # [ISP] BaseScanner ABC
│   │   │                               #   Two interfaces, not one:
│   │   │                               #   SyncScanner.scan() and AsyncScanner.scan_async()
│   │   │                               #   Scanners implement only what they support.
│   │   │
│   │   ├── static/                     # Scanners that read files, never make HTTP calls
│   │   │   ├── __init__.py
│   │   │   ├── semgrep.py              # [SRP] SemgrepScanner
│   │   │   │                           #   .scan(files, rules) → [SemgrepMatch]
│   │   │   │                           #   Handles: exec, JSON parse, timeout, per-file errors
│   │   │   │                           #   Does NOT create Evidence records (that's normalizer.py)
│   │   │   ├── semgrep_rules.py        # [SRP] SemgrepRuleManager
│   │   │   │                           #   Manages rule pack selection, version pinning, hash verify
│   │   │   │                           #   Separate from scanner: rules ≠ running
│   │   │   ├── secrets.py              # [SRP] SecretsScanner — trufflehog + pattern matching
│   │   │   ├── deps_python.py          # [SRP] PythonDepsScanner — pip-audit, safety
│   │   │   └── deps_node.py            # [SRP] NodeDepsScanner — npm audit
│   │   │                               #   ISP: split because Python and Node deps share no interface
│   │   │
│   │   └── dynamic/                    # Scanners that make HTTP calls (need ScopedHttpClient)
│   │       ├── __init__.py
│   │       ├── headers.py              # [SRP] HeadersScanner — checks security response headers
│   │       ├── cors.py                 # [SRP] CorsScanner — CORS policy validation
│   │       ├── tls.py                  # [SRP] TlsScanner — TLS version and cipher checks
│   │       ├── cookies.py              # [SRP] CookiesScanner — Secure/HttpOnly/SameSite flags
│   │       └── canary/
│   │           ├── __init__.py
│   │           ├── base.py             # [ISP] BaseCanary — .probe(url, param) → CanaryResult
│   │           ├── sql_canary.py       # [SRP] SqlCanary — 1=1 vs 1=2 behavioral diff
│   │           ├── xss_canary.py       # [SRP] XssCanary — reflection detection
│   │           ├── path_traversal_canary.py  # [SRP] PathTraversalCanary
│   │           └── ssrf_canary.py      # [SRP] SsrfCanary — callback-based (if configured)
│   │
│   │   ── providers ── (LLM Adapters — Outer Ring) ──────────────────────────
│   │
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py                     # [DIP] ProviderPort ABC — interface agents depend on
│   │   │                               #   generate_structured(prompt, schema) → BaseModel
│   │   │                               #   summarize(content, max_tokens) → str
│   │   │                               #   estimate_cost(in_tokens, out_tokens) → float
│   │   │                               #   Agents import ProviderPort. Never openai.py directly.
│   │   │
│   │   ├── openai.py                   # [SRP] OpenAIAdapter — implements ProviderPort
│   │   │                               #   gpt-4o / gpt-4o-mini, function calling, usage tracking
│   │   ├── gemini.py                   # [SRP] GeminiAdapter — implements ProviderPort
│   │   │                               #   gemini-1.5-pro / flash, response schema, usage tracking
│   │   ├── groq.py                     # [SRP] GroqAdapter — implements ProviderPort
│   │   │
│   │   ├── guard_adapter.py            # [SRP] GuardedProviderAdapter (Decorator Pattern)
│   │   │                               #   Wraps any ProviderPort:
│   │   │                               #   send → SecretRedactor → PromptGuardAgent → provider
│   │   │                               #   Agents use this, never the raw adapter directly.
│   │   │
│   │   └── retry.py                    # [SRP] RetryPolicy — exponential backoff, timeout
│   │                                   #   Applied via decorator in GuardedProviderAdapter
│   │
│   │   ── scoring ── (Domain Logic — Inner Ring) ─────────────────────────────
│   │
│   ├── scoring/
│   │   ├── __init__.py
│   │   │
│   │   │   # Each file = one scoring concern. No file knows about the others.
│   │   │   # The engine composes them. SRP taken seriously here.
│   │   │
│   │   ├── engine.py                   # [SRP] ScoringEngine — composes all 5 components
│   │   │                               #   compute(cvss, ai_prob, evidence_w, exploit, remed) → VulnScore
│   │   │                               #   Pure function. No I/O. No LLM calls.
│   │   │
│   │   ├── cvss.py                     # [SRP] CvssCalculator
│   │   │                               #   calculate(vector_string) → float (0-10)
│   │   │                               #   validate_vector(vector, evidence_type) → bool
│   │   │                               #   Pure functions. CVSS v3.1 formula only.
│   │   │
│   │   ├── calibration.py              # [SRP] ConfidenceCalibrator
│   │   │                               #   calibrate(raw_prob, category, evidence_count) → float
│   │   │                               #   Enforces caps (e.g., 0.80 cap with <2 evidence items)
│   │   │                               #   Pure function. All caps live here, not in agents.
│   │   │
│   │   ├── exploitability.py           # [SRP] ExploitabilityScorer
│   │   │                               #   score(finding_category, cvss_vector, index_tags) → float
│   │   │                               #   Pure function. OWASP membership, PoC availability.
│   │   │
│   │   └── ranking.py                  # [SRP] FindingRanker
│   │                                   #   rank([ScoredFinding]) → [ScoredFinding] sorted
│   │                                   #   check_inflation([ScoredFinding]) → InflationReport
│   │                                   #   Pure functions. No I/O.
│   │
│   │   ── storage ── (Persistence Adapters — Outer Ring) ────────────────────
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   │
│   │   │   # ISP: Four store classes. Each agent imports only the store(s) it needs.
│   │   │   # No god-object Repository that every agent imports entirely.
│   │   │
│   │   ├── base.py                     # [SRP] BaseStore — aiosqlite connection management
│   │   │                               #   get_connection(), transaction() context manager
│   │   │
│   │   ├── run_store.py                # [SRP] RunStore
│   │   │                               #   Owns: runs, events, targets, files tables
│   │   │                               #   Used by: PlannerAgent, ReconAgent, CliUiAgent
│   │   │
│   │   ├── index_store.py              # [SRP] IndexStore
│   │   ├── vector_store.py             # [SRP] ChromaDB wrapper for REPL RAG only
│   │   │                               #   Owns: index_entries table
│   │   │                               #   Used by: ReconAgent, ContextManagerAgent, PlannerAgent
│   │   │
│   │   ├── evidence_store.py           # [SRP] EvidenceStore
│   │   │                               #   Owns: evidence, findings, score_components tables
│   │   │                               #   Used by: EvidenceAgent, VulnScoringAgent, RetestAgent
│   │   │
│   │   ├── report_store.py             # [SRP] ReportStore
│   │   │                               #   Owns: reports, provider_usage, security_events tables
│   │   │                               #   Used by: ReportAgent, ContextManagerAgent
│   │   │
│   │   ├── retest_store.py             # [SRP] RetestStore
│   │   │                               #   Owns: retest_runs, policy_decisions, policy_violations
│   │   │                               #   Used by: RetestAgent, SafetyPolicyEngine
│   │   │
│   │   └── migrations/
│   │       ├── __init__.py             # Migration runner — applies migrations in order
│   │       └── 001_initial.sql         # Full schema — all tables created here (Phase 1)
│   │
│   │   ── reports ── (Export Adapters — Outer Ring) ────────────────────────
│   │
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── base.py                     # [OCP] BaseExporter ABC — .export(run_data) → str
│   │   │                               #   New formats = new class, never modify existing.
│   │   ├── markdown.py                 # [SRP] MarkdownExporter — bug-report.md rendering
│   │   │                               #   Loads artifacts from storage, renders sections
│   │   ├── sarif.py                    # [SRP] SarifExporter — SARIF 2.1.0 JSON
│   │   │                               #   validate_schema() called before write
│   │   ├── json_export.py              # [SRP] JsonExporter — machine-readable findings JSON
│   │   └── github_issue.py             # [SRP] GitHubIssueExporter — formats finding as issue body
│   │
│   │   ── tui ── (UI Adapter — Outer Ring) ────────────────────────────────
│   │
│   └── tui/
│       ├── __init__.py
│       ├── app.py                      # [SRP] BugHunterApp — Textual App, wires widgets together
│       │                               #   Subscribes to EventBus. Delegates all data to widgets.
│       │                               #   No rendering logic here.
│       ├── bughunter.tcss              # [SRP] All Textual CSS — theme, colors, layout breakpoints
│       │                               #   Zero styling in Python widget files.
│       │
│       ├── widgets/                    # One widget = one piece of UI with one data concern
│       │   ├── __init__.py
│       │   ├── header.py               # [SRP] BugHunterHeader — run ID, elapsed, model name
│       │   ├── footer.py               # [SRP] BugHunterFooter — current op, rate state, key hints
│       │   ├── phase_tracker.py        # [SRP] PhaseTrackerWidget — 8-phase pipeline, status icons
│       │   ├── agent_feed.py           # [SRP] AgentFeedWidget — scrolling agent action log
│       │   ├── findings_stream.py      # [SRP] FindingsStreamWidget — list of FindingCards
│       │   │                           #   Owns: sort order, filter state
│       │   ├── finding_card.py         # [SRP] FindingCard — one finding's display
│       │   │                           #   Owns: VulnScore bar, AI prob bar, evidence badges
│       │   │                           #   Does NOT sort or filter. That's FindingsStream's job.
│       │   └── score_summary.py        # [SRP] ScoreSummaryWidget — tier counts, top/mean, cost
│       │
│       └── modals/                     # Each modal owns one approval/interaction flow
│           ├── __init__.py
│           ├── approval.py             # [SRP] ApprovalModal — safe-active / lab / race-condition
│           │                           #   One modal for all approval types (parameterized)
│           ├── score_detail.py         # [SRP] ScoreBreakdownModal — 5-component score table
│           ├── interrupt.py            # [SRP] InterruptModal — "save partial results?" prompt
│           └── help.py                 # [SRP] HelpModal — keyboard shortcuts overlay
│
│   ── Tests ─────────────────────────────────────────────────────────────────
│
├── tests/
│   ├── conftest.py                     # Shared pytest fixtures, test DB setup, mock providers
│   ├── factories.py                    # Model factories (builder pattern for test data)
│   │
│   ├── unit/                           # Pure unit tests — no I/O, no network, all mocked
│   │   ├── models/
│   │   │   ├── test_scope.py           # Scope parsing, validation rules
│   │   │   ├── test_finding.py         # Finding status transitions
│   │   │   └── test_score.py           # VulnScore dataclass, tier assignment
│   │   │
│   │   ├── core/
│   │   │   ├── test_safety_engine.py   # PolicyDecision for all action categories
│   │   │   ├── test_scope_validator.py # Scope file validation edge cases
│   │   │   ├── test_mode_classifier.py # Scan mode classification rules
│   │   │   ├── test_rate_limiter.py    # Token bucket behavior
│   │   │   ├── test_secret_redactor.py # Pattern matching, masking output
│   │   │   └── test_content_wrapper.py # Evidence block formatting
│   │   │
│   │   ├── scoring/
│   │   │   ├── test_engine.py          # VulnScore formula with known inputs/outputs
│   │   │   ├── test_cvss.py            # CVSS v3.1 calculations, vector validation
│   │   │   ├── test_calibration.py     # Confidence caps per category, evidence count
│   │   │   ├── test_exploitability.py  # Exploit factor computation
│   │   │   └── test_ranking.py         # Sort order, inflation detection threshold
│   │   │
│   │   ├── agents/
│   │   │   ├── test_injection_classifier.py  # All injection patterns detected
│   │   │   ├── test_evidence_weight.py       # Evidence scoring table
│   │   │   ├── test_deduplicator.py          # Duplicate merging logic
│   │   │   ├── test_false_positive_filter.py # Known safe patterns pass through
│   │   │   ├── test_snippet_selector.py      # Tag ranking, token budget cutoff
│   │   │   ├── test_patch_formatter.py       # Diff output format
│   │   │   └── test_evidence_comparator.py   # Old vs new evidence → FindingStatus
│   │   │
│   │   └── reports/
│   │       ├── test_markdown_renderer.py # Section rendering, citation format
│   │       ├── test_sarif_schema.py      # SARIF output passes schema validation
│   │       └── test_json_export.py       # JSON structure and field completeness
│   │
│   ├── integration/                    # Integration tests — real tools, real SQLite, no network
│   │   ├── test_semgrep_scanner.py     # Real Semgrep against fixture files
│   │   ├── test_semgrep_rules.py       # Rule pack selection, hash pinning
│   │   ├── test_secrets_scanner.py     # Real pattern matching against sample files
│   │   ├── test_deps_scanner.py        # Real pip-audit / npm audit (mocked CVE db)
│   │   ├── test_manifest_builder.py    # Real filesystem walk, exclusion rules
│   │   ├── test_index_build.py         # Full index.md generation from fixture repo
│   │   ├── test_context_manager.py     # Snippet selection + budget enforcement
│   │   ├── test_token_budget.py        # Budget warning and hard-stop at limit
│   │   ├── test_storage_run.py         # RunStore CRUD, event recording
│   │   ├── test_storage_evidence.py    # EvidenceStore CRUD, score_components write
│   │   ├── test_storage_index.py       # IndexStore tag-based retrieval
│   │   └── test_full_report.py         # End-to-end Markdown + SARIF + JSON rendering
│   │
│   ├── security/                       # Security contract tests — must all pass before release
│   │   ├── test_scope_blocking.py      # Out-of-scope URLs blocked before sending
│   │   ├── test_passive_no_http.py     # Passive mode makes zero HTTP calls
│   │   ├── test_secret_never_sent.py   # Secrets masked before provider call (mocked provider)
│   │   ├── test_zero_evidence_gate.py  # Zero-evidence findings rejected by EvidenceAgent
│   │   └── prompt_injection/
│   │       ├── test_ignore_instructions.py   # "ignore previous instructions" quarantined
│   │       ├── test_role_override.py         # "you are now..." quarantined
│   │       ├── test_system_override.py       # [SYSTEM] in comments quarantined
│   │       ├── test_base64_injection.py      # Base64-encoded injection quarantined
│   │       ├── test_readme_injection.py      # Injection in README quarantined
│   │       ├── test_json_injection.py        # Injection in HTTP JSON body quarantined
│   │       └── test_yaml_injection.py        # role:system in YAML quarantined
│   │
│   ├── fixtures/                       # Intentionally vulnerable test applications
│   │   │
│   │   ├── vulnerable_flask_app/       # Python Flask — 7 documented vulnerabilities
│   │   │   ├── app.py                  # Main app (SQLi, IDOR, missing CSRF, CORS, path traversal)
│   │   │   ├── config.py               # Hardcoded API key, DEBUG=True
│   │   │   ├── models.py               # SQLAlchemy models (mass assignment risk)
│   │   │   ├── requirements.txt        # Outdated dep with CVE
│   │   │   ├── scope.yml               # Scope file scoped to this app
│   │   │   └── VULN_MAP.md             # File:line → vulnerability → expected tier + Semgrep rule
│   │   │
│   │   ├── vulnerable_flask_app_clean/ # All vulns fixed — expects zero findings
│   │   │   ├── app.py
│   │   │   ├── config.py
│   │   │   ├── models.py
│   │   │   └── requirements.txt
│   │   │
│   │   ├── vulnerable_express_app/     # Node.js Express — 5 documented vulnerabilities
│   │   │   ├── app.js                  # XSS, JWT alg:none, missing headers, CORS *
│   │   │   ├── package.json            # Outdated dep with CVE
│   │   │   ├── scope.yml
│   │   │   └── VULN_MAP.md
│   │   │
│   │   ├── vulnerable_express_app_clean/
│   │   │   ├── app.js
│   │   │   └── package.json
│   │   │
│   │   └── scope_files/                # Reusable scope file examples for tests
│   │       ├── passive_only.yml
│   │       ├── safe_active_local.yml
│   │       └── lab_validation.yml
│   │
│   └── e2e/                            # End-to-end tests — full pipeline against fixture apps
│       ├── conftest.py                 # Start/stop fixture app servers, cleanup
│       ├── test_flask_vuln_scan.py     # All 7 expected findings produced, correct tiers
│       ├── test_flask_clean_scan.py    # Zero findings on fixed app
│       ├── test_express_vuln_scan.py   # All 5 expected findings produced
│       ├── test_express_clean_scan.py  # Zero findings on fixed app
│       ├── test_retest_lifecycle.py    # Scan → fix → retest → findings marked fixed
│       ├── test_resume_run.py          # Interrupt mid-scan → resume → same findings
│       └── test_ci_mode.py             # Non-TTY mode, exit codes, SARIF validity
│
│   ── CI / Scripts ──────────────────────────────────────────────────────────
│
├── .github/
│   └── workflows/
│       ├── ci.yml                      # PR: ruff, mypy, pytest unit + integration + security
│       ├── e2e.yml                     # E2E: runs on merge to main (slower, needs servers)
│       └── publish.yml                 # Publish to PyPI on semver tag push
│
└── scripts/
    ├── dev-setup.sh                    # Install uv, sync deps, install Semgrep
    ├── start-fixture-servers.sh        # Start Flask + Express fixture apps for e2e
    ├── stop-fixture-servers.sh         # Clean stop of fixture servers
    └── update-semgrep-pins.sh          # Download rule packs, compute SHA256, update scope template
```

---

## Module Responsibility Summary

| Module | What it owns | What it never touches |
|---|---|---|
| `models/` | Domain data types | Storage, HTTP, LLM, TUI |
| `core/safety/` | Policy decisions, scope validation | Agents, scanners, LLM |
| `core/http/` | Scoped HTTP requests | Agent logic, storage |
| `core/events/` | Event bus, event types | Business logic |
| `core/secrets/` | Secret masking | HTTP, storage, LLM |
| `core/artifacts/` | File I/O for artifacts | Domain logic |
| `graph/` | LangGraph wiring | Agent business logic |
| `agents/*/agent.py` | Coordinate one pipeline step | Direct I/O, HTTP, rendering |
| `agents/*/[sub].py` | One focused concern per file | Other agents' concerns |
| `scanners/static/` | File-reading tools | HTTP, LLM, storage |
| `scanners/dynamic/` | HTTP-based probes | Static analysis, LLM |
| `providers/` | LLM API calls | Agent logic, storage |
| `scoring/` | VulnScore formula (pure Python) | LLM calls, I/O |
| `storage/` | SQLite CRUD | Business logic |
| `reports/` | Rendering/exporting | Agent logic, storage writes |
| `tui/` | Terminal display | Business logic, storage, HTTP |

---

## Interfaces (Ports)

The following abstractions are the "ports" that keep the architecture decoupled:

```python
# providers/base.py — agents depend on this, never on OpenAI/Gemini directly
class ProviderPort(ABC):
    @abstractmethod
    async def generate_structured(self, prompt: str, schema: type[T]) -> T: ...
    @abstractmethod
    async def summarize(self, content: str, max_tokens: int) -> str: ...
    @abstractmethod
    def estimate_cost(self, in_tok: int, out_tok: int) -> float: ...

# scanners/base.py — two interfaces, not one (ISP)
class StaticScannerPort(ABC):
    @abstractmethod
    def scan(self, files: list[Path], config: ScanConfig) -> list[RawMatch]: ...

class DynamicScannerPort(ABC):
    @abstractmethod
    async def probe(self, url: str, config: ScanConfig) -> list[RawMatch]: ...

# storage/base.py — each store is its own port (ISP)
class RunStorePort(ABC): ...
class IndexStorePort(ABC): ...
class EvidenceStorePort(ABC): ...
class ReportStorePort(ABC): ...

# reports/base.py — OCP: add formats, never modify existing
class ExporterPort(ABC):
    @abstractmethod
    def export(self, run_data: RunData) -> str: ...
```

---

## Runtime Directory (per scan)

```
.bughunter/
├── config.yml              # Provider, model, default budget, preferences
├── last-run-id             # Text file: last run UUID (for `bughunter show` shorthand)
│
└── runs/
    └── <run-uuid>/         # e.g., 20260625-143201-a3f9
        ├── scope.yml       # Snapshot of scope used (read-only after run starts)
        ├── bughunter.db    # SQLite database — ALL run data
        │
        ├── index.md        # Step 1: Codebase security index (built by ReconAgent)
        │
        ├── testing/        # Step 2: Test plans (written by PlannerAgent before execution)
        │   ├── test1.md
        │   ├── test2.md
        │   └── testN.md
        │
        ├── test-results.md # Step 3: Append-only results (written by DynamicTestAgent)
        │
        ├── bug-report.md   # Step 4: Final polished report (written by ReportAgent)
        ├── bug-report.sarif    # Optional: exported on demand
        └── bug-report.json     # Optional: exported on demand
```

---

## pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "bughunter"
version = "0.1.0"
description = "Autonomous authorized white-hat security CLI"
requires-python = ">=3.12"

dependencies = [
    # CLI
    "typer>=0.12",

    # TUI
    "textual>=0.61",
    "rich>=13",

    # Agent orchestration
    "langgraph>=0.2",
    "langchain-core>=0.2",

    # Data models
    "pydantic>=2.7",

    # Static scanning
    "semgrep>=1.80",

    # HTTP client
    "httpx>=0.27",

    # Config parsing
    "pyyaml>=6",

    # Async storage
    "aiosqlite>=0.20",

    # LLM providers
    "openai>=1.30",
    "google-generativeai>=0.7",

    # Supplementary secrets
    "trufflehog3>=3",

    # SARIF validation
    "jsonschema>=4.22",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5",
    "mypy>=1.10",
    "ruff>=0.4",
    "respx>=0.21",          # Mock httpx for unit tests
]

[project.scripts]
bughunter = "bughunter.cli:app"

[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "I", "S", "UP", "B", "C4"]

[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]
disallow_any_generics = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "unit: pure unit tests (no I/O)",
    "integration: real tools, no network",
    "security: security contract tests",
    "e2e: full pipeline tests",
]
```

---

## Dependency & Responsibility Matrix

| File / Class | SRP? | OCP? | LSP? | ISP? | DIP? | Notes |
|---|---|---|---|---|---|---|
| `cli.py` | ✅ | — | — | — | ✅ | Only dispatches. Depends on graph port. |
| `graph/builder.py` | ✅ | ✅ | — | — | ✅ | Wiring only. New nodes = new entry, not edit. |
| `agents/*/agent.py` | ✅ | — | ✅ | — | ✅ | All agents substitutable via BaseAgent. |
| `agents/planner/test_selector.py` | ✅ | — | — | — | — | Pure function. |
| `scoring/engine.py` | ✅ | — | — | — | ✅ | Depends on component interfaces only. |
| `scoring/cvss.py` | ✅ | — | — | — | — | Pure computation. |
| `scanners/static/semgrep.py` | ✅ | — | ✅ | ✅ | ✅ | Implements StaticScannerPort. |
| `scanners/dynamic/cors.py` | ✅ | — | ✅ | ✅ | ✅ | Implements DynamicScannerPort. |
| `providers/base.py` | — | ✅ | — | ✅ | — | Port definition. Agents import this only. |
| `providers/guard_adapter.py` | ✅ | — | ✅ | — | ✅ | Decorator over any ProviderPort. |
| `storage/evidence_store.py` | ✅ | — | — | ✅ | — | One store = one table group. |
| `reports/sarif.py` | ✅ | ✅ | ✅ | — | — | Implements ExporterPort. |
| `tui/widgets/finding_card.py` | ✅ | — | — | — | — | Renders one finding. No sort/filter. |

---

## Testing Strategy

| Layer | Folder | What is mocked | Coverage target |
|---|---|---|---|
| **Unit** | `tests/unit/` | Everything except the class under test | 95%+ on domain + scoring |
| **Integration** | `tests/integration/` | Network + LLM providers | 90%+ on scanners + storage |
| **Security** | `tests/security/` | LLM provider (check input, not output) | 100% on all security contracts |
| **E2E** | `tests/e2e/` | Nothing (real Semgrep, real HTTP, real SQLite) | All fixture vulns found |
| **Type** | CI (`mypy --strict`) | N/A | Zero errors, all source files |
| **Lint** | CI (`ruff check`) | N/A | Zero errors or warnings |
