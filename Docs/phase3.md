# Phase 3: Dynamic Testing and TUI Latency

## Goal

Add test planning, safe active web testing, and responsive terminal streaming. Phase 3 focuses on generating `testing/testN.md` plans before execution, running authorized HTTP checks, rate limits, progress visibility, cancellation, and partial results.

## Deliverables

- `DynamicTestAgent` implementation.
- HTTP client with scope enforcement.
- Rate limiting.
- `testing/testN.md` test plan generation.
- `test-results.md` append workflow.
- Safe active test suite.
- TUI progress model for slow graph nodes.
- Partial finding streaming.
- Cancellation and resumable run support.

## Test Plan Files

Before execution, each planned test is written to:

```text
.bughunter/runs/<run_id>/testing/testN.md
```

Each test file must include:

- Test ID and title.
- White-hat authorization statement.
- Test category.
- Source index entries used.
- Target files, routes, or endpoints.
- Test objective.
- Test method.
- Deterministic tools to run.
- AI review task, if any.
- Safety limits.
- Expected evidence.
- Todo checklist.
- Result placeholder.

The test planner should produce a balanced set across:

- White-box code tests.
- Black-box runtime tests.
- Core security baseline tests.
- Authentication and session tests.
- Authorization tests.
- Business logic tests.
- Injection and deserialization tests.
- File upload tests.
- Secret detection tests.
- Dependency and supply-chain tests.
- Client-side tests.
- Network and cloud checks.
- Race-condition tests with strict caps.
- Mobile API tests when scoped.
- Language/framework-specific tests.
- OWASP-inspired application and API security checks.

## Test Results File

After each test, append results to:

```text
.bughunter/runs/<run_id>/test-results.md
```

Each result entry must include:

- Test ID.
- Status: `passed`, `finding_created`, `blocked`, `inconclusive`, or `skipped`.
- Tools executed.
- Evidence IDs.
- Observations.
- Finding IDs created.
- False positives rejected.
- Retest guidance.

`test-results.md` is the source for the final `bug-report.md`.

## Safe Active Checks

Allowed in `safe-active` mode:

- Security header checks.
- CORS checks.
- TLS metadata checks.
- Cookie flag checks.
- Redirect behavior checks.
- Basic auth/session consistency checks.
- Rate-limit observation with low request volume.
- Safe SQL injection canaries.
- Safe XSS reflection canaries.
- Path traversal canaries without reading sensitive files.
- SSRF indicator payloads only against controlled callback/sentinel services if configured.
- Broken access-control checks only with user-provided test accounts.

Blocked unless `lab-validation`:

- Destructive exploit payloads.
- High-volume fuzzing.
- Denial-of-service tests.
- Password spraying.
- Credential stuffing.
- Persistence.
- Shell upload attempts.
- Real data exfiltration.

## Scope Enforcement

Every request must pass through the scope guard.

The guard checks:

- URL scheme.
- Host.
- Port.
- Path allow/deny rules if configured.
- Scan mode.
- Rate limit.
- Payload category.

Requests outside the scope must be rejected and logged as blocked events.

## Latency Strategy

The TUI must stay active while DynamicTestAgent or model calls are slow.

Required UI behavior:

- Show active endpoint.
- Show current check category.
- Show completed/total checks where known.
- Show elapsed time.
- Show rate-limit wait states.
- Show model waiting state.
- Stream partial observations before final findings.
- Allow user cancellation.
- Save partial run data before exiting.

Heartbeat events should be emitted at regular intervals during long waits:

- `model_waiting`
- `tool_progress`
- `rate_limited`
- `still_running`

The UI must avoid fake progress. If exact progress is unknown, show the current operation and elapsed time instead of a misleading percentage.

## Todo List

- [ ] Implement scoped HTTP client.
- [ ] Implement rate limiter.
- [ ] Implement test plan writer for `.bughunter/runs/<run_id>/testing/testN.md`.
- [ ] Implement test results appender for `.bughunter/runs/<run_id>/test-results.md`.
- [ ] Implement language-aware test category selection from `index.md`.
- [ ] Add reusable test category registry matching `Docs/test-library.md`.
- [ ] Classify every test as `passive`, `safe-active`, `lab-validation`, or `blocked`.
- [ ] Implement request/response evidence capture.
- [ ] Implement security header checks.
- [ ] Implement CORS checks.
- [ ] Implement cookie checks.
- [ ] Implement safe canary payload framework.
- [ ] Implement DynamicTestAgent.
- [ ] Implement heartbeat events.
- [ ] Implement cancellation handling.
- [ ] Persist partial findings during runs.
- [ ] Add tests for out-of-scope request blocking.
- [ ] Add tests for rate limiting.
- [ ] Add tests against a local vulnerable fixture app.

## Acceptance Criteria

Phase 3 is complete when:

- Test plans are written before execution.
- `test-results.md` is updated after each test.
- Safe active checks run only against scoped targets.
- The CLI blocks out-of-scope requests before sending them.
- Long scans show useful terminal progress.
- Partial findings appear before the full scan finishes.
- Interrupted runs preserve enough state to generate a partial report.
