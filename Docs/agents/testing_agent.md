# DynamicTestAgent

## Purpose

DynamicTestAgent performs authorized, safe active web testing against scoped targets.

It validates runtime behavior without damaging availability, exfiltrating data, or attacking credentials.

## Inputs

- Scope file.
- Target URLs.
- Scan mode.
- `testing/testN.md` files.
- Route map from ReconAgent.
- Test accounts if provided.
- Rate limits.
- Safety policy.

## Outputs

- HTTP evidence records.
- Dynamic findings.
- Appended entries in `test-results.md`.
- Blocked request events.
- Rate-limit events.
- Retest data.

## Allowed Safe Checks

- Security headers.
- CORS behavior.
- Cookie flags.
- TLS metadata.
- Redirect behavior.
- Safe reflection canaries.
- Safe injection canaries.
- Auth/session consistency.
- Low-volume rate-limit observation.
- Path traversal canaries that do not read sensitive system files.

## Black-Box Testing Role

DynamicTestAgent owns black-box runtime testing. It should execute only the tests documented in `testing/testN.md`, and it must append results to `test-results.md` after each test.

The agent should prioritize:

- HTTP security headers.
- CORS.
- Cookie security.
- Auth/session behavior.
- Access-control behavior.
- Safe input reflection checks.
- Safe injection canaries.
- Low-impact network exposure checks.
- Business logic checks using test data.
- Race-condition checks with strict concurrency caps.
- Upload checks with benign files only.
- Cloud exposure checks only for scoped assets.

## Blocked By Default

- Denial-of-service tests.
- Password spraying.
- Credential stuffing.
- Destructive exploit payloads.
- Persistence.
- Shell upload attempts.
- Real data exfiltration.
- Unbounded fuzzing.

## Scope Guard

Every request must pass the scoped HTTP client.

The agent must never construct and send raw requests outside that client.

The client enforces:

- Allowed hosts.
- Allowed ports.
- Scan mode.
- Rate limits.
- Payload category.
- Timeout.

## Latency Events

Dynamic tests can take time. The agent must emit:

- Current endpoint.
- Current check.
- Completed checks count.
- Rate-limit waiting.
- HTTP timeout warnings.
- Partial observations.
- Confirmed findings.

## Todo List

- [ ] Implement scoped HTTP request interface.
- [ ] Implement safe check registry.
- [ ] Load and execute `testing/testN.md` plans.
- [ ] Append each completed test to `test-results.md`.
- [ ] Enforce per-test safety classification before execution.
- [ ] Add strict concurrency caps for race-condition tests.
- [ ] Implement response evidence capture.
- [ ] Implement blocked request logging.
- [ ] Implement rate-limit wait events.
- [ ] Add integration tests with local vulnerable app.
