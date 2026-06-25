# Phase 4: LangGraph Orchestration, Reports, and Retesting

## Goal

Connect the planner, recon, index, test planning, static audit, dynamic testing, evidence, fix, and report components into a complete autonomous workflow.

## Deliverables

- LangGraph orchestration.
- Provider adapters for OpenAI and Gemini.
- ReportAgent with polished Markdown output.
- Final `bug-report.md` generation from `index.md`, `testing/testN.md`, `test-results.md`, and stored evidence.
- FixAgent for concrete remediation guidance.
- Retest workflow.
- Run resume support.
- Final integration tests.

## Graph Flow

Default flow:

1. Load scope.
2. Validate safety policy.
3. Create run record.
4. PlannerAgent creates scan plan.
5. ReconAgent builds target and repository map.
6. ReconAgent writes `index.md`.
7. PlannerAgent writes `testing/testN.md` files from the index.
8. StaticAuditAgent produces code findings.
9. DynamicTestAgent produces web findings when targets are present.
10. EvidenceAgent normalizes and deduplicates evidence.
11. Each test appends results to `test-results.md`.
12. FixAgent proposes remediation.
13. ReportAgent writes `bug-report.md`.
14. RetestAgent records validation steps or reruns safe checks.

The graph should support skipping dynamic tests when no URL is scoped.

## Provider Adapters

Implement:

- OpenAI adapter.
- Gemini adapter.
- Shared structured output parser.
- Retry and timeout handling.
- Usage tracking.
- Redaction of secrets before prompts.

The graph should receive normalized model responses only.

## Report Quality

The final `bug-report.md` should be suitable for:

- GitHub issue creation.
- Security audit handoff.
- Portfolio demonstration.
- Developer remediation.

Required sections:

- Executive summary.
- Scope and scan mode.
- Codebase index summary.
- Tests executed.
- Blocked or skipped tests.
- Policy violations and safety downgrades.
- Risk table.
- Findings by severity.
- Detailed findings.
- Evidence.
- Fix guidance.
- Retest checklist.
- Appendix with tool/model metadata.

The report must cite:

- The `index.md` entries used to locate the issue.
- The `testing/testN.md` plan that produced the result.
- The `test-results.md` result entry.
- Stored evidence IDs.

## Retesting

Retesting should:

- Reuse original scope.
- Rerun only checks related to selected findings where possible.
- Compare previous and current evidence.
- Mark findings as `fixed`, `still_present`, `not_retested`, or `inconclusive`.
- Generate a retest report section.

## Todo List

- [ ] Implement LangGraph state model.
- [ ] Implement PlannerAgent node.
- [ ] Connect `index.md` generation into the graph before audit/test execution.
- [ ] Connect `testing/testN.md` generation before execution.
- [ ] Connect `test-results.md` append events after every test.
- [ ] Connect ReconAgent, StaticAuditAgent, and DynamicTestAgent.
- [ ] Implement EvidenceAgent deduplication.
- [ ] Implement FixAgent.
- [ ] Implement ReportAgent for final `bug-report.md`.
- [ ] Include blocked tests, policy violations, and safety downgrades in reports.
- [ ] Separate confirmed bugs from likely, possible, and informational findings.
- [ ] Implement OpenAI provider adapter.
- [ ] Implement Gemini provider adapter.
- [ ] Implement model timeout and retry policy.
- [ ] Implement token and cost tracking.
- [ ] Implement retest command.
- [ ] Add end-to-end tests.
- [ ] Add documentation examples.

## Acceptance Criteria

Phase 4 is complete when:

- `bughunter` can run an interactive end-to-end scan.
- OpenAI and Gemini can be selected through config.
- Findings are evidence-backed and fix-ready.
- `index.md`, `testing/testN.md`, `test-results.md`, and `bug-report.md` are produced in order.
- Reports include confidence status and safety policy outcomes.
- Reports are polished, reproducible, and traceable back to tests.
- Retesting can update finding status.
- End-to-end tests pass against fixture apps.
