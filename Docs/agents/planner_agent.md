# PlannerAgent

## Purpose

PlannerAgent converts the user request and `bughunter-scope.yml` into a safe, executable scan plan.

It decides what phases should run, but it does not perform scanning itself.

## Inputs

- User prompt or CLI command.
- Parsed scope file.
- Provider configuration.
- Previous run state if resuming.
- Available deterministic tools.
- `index.md` entries after ReconAgent completes.

## Outputs

- Scan plan.
- Enabled agents.
- Scan mode.
- Target list.
- Safety constraints.
- Expected evidence types.
- Estimated work units for TUI progress.
- Planned test files under `.bughunter/runs/<run_id>/testing/`.

## Responsibilities

- Validate that requested work fits the scope.
- Choose passive, safe-active, or lab-validation behavior.
- Decide whether dynamic testing should run.
- Decide which deterministic tools are relevant.
- Generate `testing/testN.md` files from `index.md`.
- Select white-box, black-box, core, language-specific, network, and OWASP-style tests based on the detected stack.
- Emit an initial progress plan for the TUI.
- Refuse or downgrade unsafe requests.

## Planning Rules

PlannerAgent should prefer narrow, evidence-first plans.

Good plan:

- Map repository.
- Build `index.md`.
- Identify routes and auth code.
- Create test files before running them.
- Run deterministic scanners.
- Review selected snippets with AI.
- Run safe HTTP checks against scoped local URL.
- Generate report.

Bad plan:

- Ask AI to read the entire codebase.
- Run exploit payloads against unknown internet targets.
- Perform high-volume fuzzing by default.
- Generate findings without evidence.

## Test Selection Rules

PlannerAgent must use the detected language, framework, and index tags to choose tests.

Baseline categories:

- White-box source review.
- Black-box runtime checks.
- Core security checks.
- OWASP Web and API risk categories.
- Authentication and session flaws.
- Authorization flaws, especially IDOR/BOLA.
- Business logic flaws.
- Injection and deserialization.
- File upload weaknesses.
- Secret exposure.
- Dependency and supply-chain risk.
- Client-side security.
- Network and cloud exposure.
- Race-condition risks.
- Mobile API risks when scoped.
- Language/framework-specific risks.
- Network and HTTP exposure checks.

Every generated test file must include a white-hat authorization statement and a safety limit section.

The planner should not generate tests that require destructive exploitation, credential attacks, persistence, or denial-of-service behavior.

PlannerAgent must classify every selected test as `passive`, `safe-active`, `lab-validation`, or `blocked`. Blocked tests should be documented as blocked results when relevant, not executed.

## Todo List

- [ ] Define scan plan schema.
- [ ] Define test plan artifact schema.
- [ ] Implement scope-aware planning prompt.
- [ ] Implement `testing/testN.md` generation from `index.md`.
- [ ] Implement language/framework-aware test selection.
- [ ] Implement test category registry from `Docs/test-library.md`.
- [ ] Implement scan-mode classification for each selected test.
- [ ] Implement unsafe request downgrade/refusal logic.
- [ ] Emit estimated work units.
- [ ] Add tests for safe-active and lab-validation decisions.
