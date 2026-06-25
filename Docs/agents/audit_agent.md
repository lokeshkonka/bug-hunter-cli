# StaticAuditAgent

## Purpose

StaticAuditAgent audits local source code using deterministic evidence and bounded AI evaluation.

It should not directly consume the entire repository. It receives compact audit packets produced by ReconAgent and deterministic scanners.

## Inputs

- Repository manifest.
- Relevant `index.md` entries.
- Ranked file list.
- Snippets with line ranges.
- Deterministic scanner matches.
- Scope constraints.
- Prior evidence.

## Outputs

- Candidate findings.
- Confirmed static findings.
- False-positive notes.
- Test result updates for `test-results.md`.
- Fix guidance requests for FixAgent.
- Events for CLI streaming.

## Deterministic First Workflow

1. Receive selected `index.md` entries.
2. Retrieve only the required snippets.
3. Receive deterministic matches.
4. Ask model to classify risk and confidence.
5. Require evidence before confirming finding.
6. Store finding with file path, line range, test ID, and evidence ID.
7. Append the test outcome to `test-results.md`.

## Vulnerability Categories

Initial categories:

- Hardcoded secrets.
- Insecure configuration.
- SQL injection risk.
- Command execution risk.
- SSRF risk.
- Path traversal risk.
- Unsafe file upload.
- Broken access control indicators.
- Insecure CORS.
- Missing authentication middleware.
- Debug mode exposure.

## Context Rules

Do not send:

- Entire repository.
- Dependency folders.
- Generated files.
- Large logs.
- Binary files.

Send:

- Relevant `index.md` entries.
- Relevant snippets.
- File path.
- Line range.
- Reason selected.
- Scanner match metadata.
- Framework summary.

## White-Box Testing Role

StaticAuditAgent owns white-box testing. It should use code structure, routes, data flow, and security-sensitive index tags to validate risks without reading unrelated files.

The agent should focus on:

- Source-to-sink paths.
- Missing auth or authorization checks.
- Unsafe input handling.
- Secret exposure.
- Dangerous framework configuration.
- Language-specific risky APIs.

## Todo List

- [ ] Define audit packet schema.
- [ ] Add `index.md` entry references to audit packets.
- [ ] Implement scanner result normalization.
- [ ] Implement structured model output.
- [ ] Implement confidence scoring.
- [ ] Implement duplicate grouping.
- [ ] Add tests using vulnerable fixture files.
