# CliUiAgent

## Purpose

CliUiAgent owns the terminal experience. It makes long-running scans observable, interactive, and understandable without exposing hidden model chain-of-thought.

## Responsibilities

- Render run phases.
- Render active agent.
- Render tool progress.
- Render waiting states.
- Render finding counters.
- Render confirmed findings.
- Render index generation progress.
- Render test plan generation progress.
- Render `test-results.md` updates.
- Show report paths.
- Handle cancellation.
- Show resumable run information.

## Latency Strategy

LLM calls and graph nodes can be slow. The UI must avoid looking frozen.

Required behavior:

- Show elapsed time for long operations.
- Show spinner or activity indicator.
- Show `model_waiting` messages during LLM calls.
- Show deterministic tool progress while scanning files or endpoints.
- Show which `index.md` section or `testing/testN.md` file is active.
- Show partial findings immediately.
- Show rate-limit wait messages.
- Allow safe cancellation.
- Flush partial run state before exit.

The UI must not fake exact percentages when total work is unknown.

## Event Types To Render

- `phase_started`
- `tool_started`
- `tool_progress`
- `model_waiting`
- `observation`
- `finding_candidate`
- `finding_confirmed`
- `index_written`
- `test_plan_written`
- `test_result_written`
- `rate_limited`
- `blocked_by_scope`
- `phase_completed`
- `report_written`
- `error`

## Display Rules

Show:

- Actions.
- Observations.
- Evidence summaries.
- Artifact paths.
- Risk changes.
- User approvals.
- Errors and blocked actions.

Do not show:

- Hidden model chain-of-thought.
- Raw secrets.
- Full sensitive responses.
- Overly verbose logs by default.

## Todo List

- [ ] Define terminal event renderer.
- [ ] Implement interactive run screen.
- [ ] Implement compact headless output.
- [ ] Implement finding summary panel.
- [ ] Render `index.md`, test plan, test result, and bug report artifact paths.
- [ ] Implement cancellation keybinding.
- [ ] Implement resume prompt for interrupted runs.
- [ ] Add snapshot-style CLI output tests where practical.
