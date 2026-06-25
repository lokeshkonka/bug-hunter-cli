# Phase 1: Foundation, Safety, and CLI Skeleton

## Goal

Create the project foundation for Bug Hunter CLI. Phase 1 should make the tool installable, configurable, safe by default, and capable of producing a minimal structured scan report from deterministic local checks.

This phase does not need full AI autonomy yet. It should establish the architecture that later phases will build on.

## Deliverables

- Python package scaffold using `uv`.
- `bughunter` CLI entrypoint.
- Basic interactive TUI shell.
- `bughunter-scope.yml` parser and validator.
- Provider config model for OpenAI and Gemini.
- SQLite run database.
- Event streaming model.
- Finding and evidence schemas.
- Minimal Markdown report generator.
- Safety policy enforcement for scan modes.
- Strict AI and white-hat safety contract enforcement.

## Commands To Support

```bash
bughunter
bughunter config
bughunter scan --scope bughunter-scope.yml
bughunter report --run <run_id>
bughunter runs
```

## Scope File

The MVP scope file should support:

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

safety:
  allow_lab_validation: false
  notes: "Authorized local development target"
```

Validation rules:

- Network scans require at least one URL or host.
- URLs must be explicit; no wildcard internet scanning in MVP.
- `safe-active` is the default.
- `lab-validation` requires `allow_lab_validation: true`.
- Out-of-scope hosts must be blocked before any request is made.

## Data Models

Define typed models for:

- `Run`
- `Scope`
- `Target`
- `Event`
- `Evidence`
- `Finding`
- `Report`
- `ProviderConfig`
- `SafetyPolicy`
- `PolicyDecision`
- `PolicyViolation`

Findings must include:

- `id`
- `title`
- `severity`
- `confidence`
- `category`
- `affected_component`
- `evidence_ids`
- `impact`
- `reproduction_steps`
- `recommendation`
- `retest_steps`

## Event Streaming

Implement a single internal event bus used by both CLI and future TUI.

Required event fields:

- `run_id`
- `timestamp`
- `type`
- `agent`
- `message`
- `metadata`

Initial event types:

- `phase_started`
- `tool_started`
- `tool_progress`
- `observation`
- `finding_candidate`
- `finding_confirmed`
- `phase_completed`
- `report_written`
- `error`

## Minimal Checks

Phase 1 should include deterministic checks only:

- Detect dependency manifests.
- Detect obvious secret patterns in source files.
- Detect environment templates.
- Detect missing security headers only if a scoped URL is provided.
- Detect risky config flags such as debug mode.

AI is optional in Phase 1. If provider config exists, it can summarize deterministic findings, but it must not invent findings without evidence.

## Safety Foundation

Phase 1 must introduce a central `SafetyPolicyEngine`.

The engine should:

- Validate scope before scans.
- Classify tests as `passive`, `safe-active`, `lab-validation`, or `blocked`.
- Block out-of-scope network targets.
- Block destructive categories.
- Record blocked actions as policy violations.
- Redact secret-like values before display or model calls.

## TUI Requirements

The first TUI can be simple but must prove the streaming model:

- Show run status.
- Show current phase.
- Show recent events.
- Show finding count by severity.
- Show report path when complete.
- Show spinner or waiting state for long tasks.

Do not display hidden chain-of-thought.

## Todo List

- [ ] Create `pyproject.toml` with CLI entrypoint.
- [ ] Add package structure under `bughunter/`.
- [ ] Implement Typer CLI.
- [ ] Implement scope file loader and validator.
- [ ] Implement provider config model.
- [ ] Implement SQLite storage.
- [ ] Implement event bus.
- [ ] Implement finding and evidence schemas.
- [ ] Implement safety policy checks.
- [ ] Implement `SafetyPolicyEngine`.
- [ ] Implement `PolicyDecision` and `PolicyViolation` records.
- [ ] Add prompt-injection and secret-redaction rules.
- [ ] Implement deterministic secret/config/dependency checks.
- [ ] Implement minimal Markdown report renderer.
- [ ] Add tests for scope validation.
- [ ] Add tests for safety policy blocking.
- [ ] Add tests for report rendering.
- [ ] Add README quickstart.

## Acceptance Criteria

Phase 1 is complete when:

- `bughunter scan --scope bughunter-scope.yml` creates a run.
- Out-of-scope URLs are blocked.
- Deterministic findings are stored with evidence.
- `bughunter report --run <run_id>` writes Markdown.
- The terminal shows streaming progress events.
- Tests pass for scope, storage, safety, and report generation.
