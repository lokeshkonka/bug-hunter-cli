# Phase 2: Recon and Static Audit Pipeline

## Goal

Build the codebase-aware audit pipeline. Phase 2 makes Bug Hunter CLI useful for local repository auditing by mapping the project, creating a reusable `index.md`, selecting relevant files, running deterministic analysis, and using AI only on compact evidence bundles.

## Deliverables

- `ReconAgent` implementation.
- `StaticAuditAgent` implementation.
- Repository manifest builder.
- `index.md` generator.
- Index entry storage and retrieval.
- Context filtering and chunking system.
- Deterministic file scanners.
- AI summarization and finding evaluation over bounded snippets.
- Evidence-backed static findings.

## Repository Manifest

Before any LLM call, build a manifest containing:

- Project root.
- Language/framework indicators.
- Dependency manifests.
- Route files.
- Middleware files.
- Config files.
- Auth-related files.
- Database access files.
- Upload or file-processing paths.
- Test files.
- Ignored files and reasons.

Default ignored paths:

- `.git/`
- `.venv/`
- `venv/`
- `node_modules/`
- `dist/`
- `build/`
- `.next/`
- `.cache/`
- lock files unless dependency scanning needs them
- generated files
- binaries and media

## Codebase Index

After the manifest is built, ReconAgent creates `.bughunter/runs/<run_id>/index.md`.

The index is a compact security navigation document. It should let later agents identify the exact files, routes, symbols, and line ranges to inspect without rereading the entire repository.

Required sections:

- Project summary.
- Language and framework detection.
- Entry points.
- API and route map.
- Authentication and authorization map.
- Data storage and database map.
- File upload and parsing surfaces.
- External network call surfaces.
- Config and secret surfaces.
- Admin or privileged functionality.
- Dependency and package risk surfaces.
- Security-sensitive file index.
- Suggested test areas.

Each entry should include:

- Path.
- Symbol, function, class, route, or config key where available.
- Line range or approximate location.
- Security relevance.
- Retrieval tags.
- Related test category.

Example tags:

- `auth`
- `access-control`
- `sql`
- `xss`
- `ssrf`
- `upload`
- `path-traversal`
- `cors`
- `secrets`
- `admin`
- `dependency`
- `network`

## Context Window Strategy

The audit pipeline must never send the entire repo to the model.

Required flow:

1. ReconAgent builds a repository manifest.
2. ReconAgent writes `index.md` and stores index entries.
3. Deterministic scanners produce candidate evidence.
4. Files are ranked by index tags and security relevance.
5. Relevant snippets are extracted with line ranges.
6. Snippets are grouped into small audit packets.
7. StaticAuditAgent asks the model to evaluate only those packets.
8. Findings are stored only when linked to evidence.

Audit packets should include:

- Scan goal.
- Scope.
- Framework summary.
- Relevant `index.md` entries.
- File path.
- Line range.
- Snippet.
- Why this snippet was selected.
- Deterministic matches.

## Deterministic Static Checks

Implement deterministic scanners for:

- Secret patterns.
- Debug flags.
- Hardcoded credentials.
- Insecure CORS.
- Missing auth checks on likely protected routes.
- Dangerous deserialization.
- Unsafe command execution.
- SQL query construction.
- File upload handling.
- Path traversal risks.
- SSRF sink patterns.
- Dependency vulnerabilities where local tooling is available.

The AI may refine severity and fix guidance, but the raw matches must come from deterministic scanners.

## AI Role

AI is used for:

- Ranking risk.
- Explaining impact.
- Reducing false positives.
- Creating reproduction steps.
- Suggesting fixes.
- Grouping duplicate findings.

AI is not used for:

- Claiming a file exists.
- Claiming a line is vulnerable without evidence.
- Reading the whole codebase directly.
- Running commands directly.

## Todo List

- [ ] Implement repository manifest builder.
- [ ] Implement `index.md` writer.
- [ ] Implement index entry schema and SQLite storage.
- [ ] Implement index lookup by tag, file, route, and vulnerability category.
- [ ] Implement ignore rules.
- [ ] Implement file relevance scoring.
- [ ] Implement snippet extraction with line numbers.
- [ ] Implement audit packet format.
- [ ] Implement deterministic scanner interface.
- [ ] Add scanners for secrets, configs, command execution, SQL, upload, and SSRF patterns.
- [ ] Implement StaticAuditAgent model prompt using structured output.
- [ ] Store model-reviewed findings with evidence references.
- [ ] Add duplicate finding merger.
- [ ] Add tests with small vulnerable fixture projects.

## Acceptance Criteria

Phase 2 is complete when:

- `.bughunter/runs/<run_id>/index.md` is created before deeper tests run.
- Later audit steps can retrieve targeted files and snippets from index entries.
- A local repo can be scanned without exhausting model context.
- Static findings include exact file references and evidence.
- The model only receives selected snippets, not the whole repo.
- False-positive reduction happens after deterministic matching.
- Reports include static findings with fix guidance.
