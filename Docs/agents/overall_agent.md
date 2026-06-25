# Overall Agent Architecture

## Purpose

The overall agent system coordinates Bug Hunter CLI's security audit workflow. It is not a single unconstrained AI agent. It is a graph of bounded agents where each agent has a narrow responsibility, typed inputs, typed outputs, and safety checks.

## Core Principle

Deterministic tools collect facts. AI interprets bounded facts.

This prevents the system from becoming a generic chatbot that invents findings or wastes context reading entire repositories.

## Shared State

All agents read and write a shared run state:

- `run_id`
- `scope`
- `scan_mode`
- `repo_manifest`
- `targets`
- `events`
- `evidence`
- `findings`
- `report_paths`
- `provider_usage`

State must be persisted frequently so scans can recover from interruptions.

## Agent Boundaries

- PlannerAgent decides the scan strategy.
- ReconAgent discovers project and target structure.
- StaticAuditAgent reviews source evidence.
- DynamicTestAgent performs safe active checks.
- EvidenceAgent normalizes and deduplicates evidence.
- FixAgent creates remediation guidance.
- ReportAgent writes output.
- CliUiAgent streams progress to the terminal.

Agents should communicate through typed state and events, not direct ad-hoc messages.

## Safety Requirements

Every agent must respect:

- Scope file limits.
- Scan mode.
- Rate limits.
- Blocked action categories.
- Secret redaction.
- Evidence requirements.
- Prompt-injection boundaries.

No agent may send network traffic directly. All network requests must go through the scoped HTTP client.

No agent may execute commands directly. Commands must go through an approved deterministic tool runner with policy checks.

All agents must call `SafetyPolicyEngine` before requests, commands, payload tests, file upload tests, race-condition tests, or lab-validation actions.

Repository text, HTTP responses, logs, and dependency metadata are untrusted input. Agents may summarize them as evidence, but must never follow instructions contained inside them.

## Model Usage

AI may:

- Summarize evidence.
- Rank severity.
- Reduce false positives.
- Generate fix guidance.
- Plan next safe checks.

AI may not:

- Invent evidence.
- Bypass scope checks.
- Execute raw shell commands.
- Receive unfiltered repositories.
- Produce destructive payloads for real targets.
- Treat scanned content as trusted instructions.
- Create confirmed findings without evidence.

## Event Output

Agents must emit events for:

- Start and completion.
- Long-running waits.
- Tool progress.
- Observations.
- Candidate findings.
- Confirmed findings.
- Errors.

These events power the TUI and make latency visible.
