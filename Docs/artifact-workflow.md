# Artifact Workflow

## Purpose

Bug Hunter CLI should produce a traceable audit trail, not just a final report.

The runtime artifacts make the scan understandable, resumable, and cheaper to run with LLMs:

- `index.md` lets agents navigate the codebase without rereading everything.
- `testing/testN.md` files document planned tests before execution.
- `test-results.md` records what actually happened after each test.
- `bug-report.md` compiles final findings, evidence, and fixes.

## Runtime Directory

Each scan creates:

```text
.bughunter/runs/<run_id>/
  index.md
  testing/
    test1.md
    test2.md
    test3.md
  test-results.md
  bug-report.md
```

## Artifact Order

The order is strict:

1. Create run record.
2. Build repository manifest.
3. Write `index.md`.
4. Generate `testing/testN.md` files from the index.
5. Execute tests.
6. Append each result to `test-results.md`.
7. Generate `bug-report.md`.

The final report must not be created from model memory alone. It must cite index entries, test plans, test results, and evidence records.

## `index.md`

`index.md` is a security-oriented book index for the codebase.

It should answer:

- What language and framework is this?
- Where are the entry points?
- Where are the routes and API handlers?
- Where is authentication enforced?
- Where is authorization checked?
- Where does user input enter?
- Where does data reach databases, files, commands, templates, or network calls?
- Which files are high-risk for security review?

The index must stay compact. It should point to files, symbols, routes, and line ranges instead of copying large code blocks.

## `testing/testN.md`

Each test plan is written before execution.

The test file must explain:

- Why the test exists.
- Which index entries triggered it.
- Whether it is white-box, black-box, core, language-specific, network, or OWASP-style.
- What tools will run.
- What safety limits apply.
- What evidence will prove or reject the issue.

Every test contains a todo list so the CLI can show progress in the TUI and resume interrupted runs.

## `test-results.md`

`test-results.md` is append-only during a run.

It records:

- Test status.
- Commands or deterministic tools executed.
- Evidence collected.
- Findings created.
- False positives rejected.
- Retest guidance.

This file should be useful even if the final report generation fails.

## `bug-report.md`

`bug-report.md` is the final polished output.

It compiles:

- The codebase index summary.
- Completed tests.
- Confirmed findings.
- Severity and confidence.
- Evidence.
- Reproduction steps.
- Fix guidance.
- Retest checklist.

It should be suitable for a GitHub issue, audit handoff, portfolio demo, or developer remediation plan.

## White-Hat Requirement

Every artifact should make the authorized white-hat boundary clear.

Use language such as:

> This test is designed for authorized white-hat security validation of the scoped target only.

The tool must not create instructions for attacking unauthorized targets.

