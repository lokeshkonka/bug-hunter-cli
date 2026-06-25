# Security Test Library

## Purpose

Bug Hunter CLI should maintain a structured test library so PlannerAgent can select tests based on the codebase index, detected language/framework, scoped runtime targets, and scan mode.

The test library is not a list of unrestricted exploit actions. Every test must run under the white-hat safety policy:

- Authorized targets only.
- Scope file required for network testing.
- Deterministic evidence first.
- Safe canaries instead of destructive payloads.
- Lab-only handling for tests that could affect availability or upload harmful content.

## Directory Architecture

Reusable test definitions should follow this taxonomy:

```text
tests/
  core/
  owasp-web/
  owasp-api/
  auth/
  authorization/
  business-logic/
  injection/
  upload/
  secrets/
  dependency/
  client-side/
  network/
  cloud/
  race-condition/
  mobile-api/
  language-specific/
  whitebox/
  blackbox/
```

During a run, PlannerAgent converts selected definitions into `.bughunter/runs/<run_id>/testing/testN.md`.

## Test Definition Shape

Each reusable test definition should include:

- Test ID.
- Category.
- Required scan mode.
- Required scope fields.
- Required index tags.
- Supported languages/frameworks.
- Deterministic tools.
- Safe validation method.
- Evidence requirements.
- Blocked behavior.
- Report mapping.

## Categories

### Core

- Security headers.
- TLS metadata.
- Cookie flags.
- CORS policy.
- Clickjacking protections.
- Debug mode exposure.
- Error leakage.
- Sensitive file exposure.

### OWASP Web

- Broken access control.
- Cryptographic failures.
- Injection.
- Insecure design.
- Security misconfiguration.
- Vulnerable and outdated components.
- Identification and authentication failures.
- Software and data integrity failures.
- Security logging and monitoring gaps.
- SSRF.

### OWASP API

- BOLA/IDOR.
- Broken authentication.
- Broken object property authorization.
- Unrestricted resource consumption checks using safe limits only.
- Broken function-level authorization.
- Mass assignment.
- Security misconfiguration.
- Injection.
- Improper inventory management.
- Unsafe API consumption.

### Authentication and Sessions

- JWT weakness checks.
- Session fixation.
- Broken logout.
- Remember-me token weaknesses.
- Password reset issues.
- MFA bypass indicators.
- Cookie flag and session lifetime checks.

Safe approach:

- Use static review and configured test accounts where available.
- Do not brute-force credentials.
- Do not bypass MFA against real users.
- Validate only scoped flows and user-provided test identities.

### Authorization

- IDOR/BOLA.
- Horizontal privilege escalation.
- Vertical privilege escalation.
- Missing role checks.
- Mass assignment.
- Object property authorization.

Safe approach:

- Prefer white-box route and permission mapping from `index.md`.
- Use user-provided low-privilege and high-privilege test accounts for runtime checks.
- Never access real user data outside the provided test scope.

### Business Logic

- Coupon abuse.
- Negative quantity handling.
- Double spending indicators.
- Workflow bypass.
- Payment manipulation.
- Inventory bypass.
- OTP reuse.
- Duplicate transaction risk.

Safe approach:

- Prefer local/staging targets and test accounts.
- Use low-value test data only.
- Do not execute real payments or real financial transactions.
- Race and duplicate-request tests must use strict request limits.

### Injection and Deserialization

- SQL injection.
- NoSQL injection.
- LDAP injection.
- SSTI.
- XXE.
- Command injection.
- Template injection.
- Unsafe deserialization.

Safe approach:

- Use canary payloads that prove reflection or parser behavior without damage.
- Prefer static source-to-sink analysis before runtime validation.
- Never execute payloads intended to open shells, modify data, or exfiltrate files.

### File Upload

- MIME bypass.
- Extension bypass.
- SVG XSS.
- Archive handling risks.
- Malware upload control checks.
- Path traversal.

Safe approach:

- Use benign test files only.
- Do not upload real malware.
- Do not generate real ZIP bombs.
- Archive bomb checks should be static, metadata-based, or lab-only with strict resource limits.
- SVG XSS checks should use harmless canaries.

### Secrets

- API keys.
- AWS credentials.
- JWT secrets.
- Private keys.
- `.env` files.
- Hardcoded tokens.

Safe approach:

- Redact detected values in prompts, logs, reports, and artifacts.
- Store only fingerprints or masked previews.
- Never send raw secrets to AI providers.

### Dependency and Supply Chain

- Known CVEs.
- Outdated packages.
- Dependency confusion indicators.
- Typosquatting indicators.
- Suspicious install scripts.
- Lockfile drift.

Safe approach:

- Use package manifests and lockfiles.
- Prefer local advisories or official vulnerability databases when available.
- Do not install or execute unknown dependencies during audit.

### Client-Side Security

- DOM XSS.
- CSP weakness.
- CORS misconfiguration.
- Clickjacking.
- LocalStorage token leakage.
- Sensitive source map exposure.

Safe approach:

- Use static bundle/source review where possible.
- Use safe reflection canaries for runtime checks.
- Do not attempt user session theft.

### Network

- Exposed ports in scoped hosts.
- HTTP service metadata.
- TLS configuration.
- Admin panel exposure.
- Debug endpoint exposure.

Safe approach:

- No broad internet scanning in MVP.
- No high-volume port scanning.
- Only scoped hosts and rate-limited probes.

### Cloud and Infrastructure

- Exposed S3-compatible buckets.
- Kubernetes dashboard exposure.
- Docker API exposure.
- Redis without auth.
- Elasticsearch exposure.
- Environment variable leaks.
- Metadata service SSRF indicators.

Safe approach:

- Check only scoped assets.
- Prefer passive discovery from code/config/IaC.
- Do not enumerate unrelated cloud resources.
- Do not access or download bucket contents unless explicitly authorized.

### Race Condition

- Multiple simultaneous requests.
- Duplicate transactions.
- OTP reuse.
- Inventory bypass.
- Coupon reuse.
- Idempotency failures.

Safe approach:

- Run only with explicit safe-active approval.
- Use strict concurrency caps.
- Use test accounts and test data.
- Never target production payment flows unless explicitly scoped and configured for test transactions.

### Mobile API

- Hidden endpoints.
- API replay risks.
- Insecure token storage indicators.
- Certificate pinning configuration review.
- Mobile-specific auth flow weaknesses.

Safe approach:

- MVP should focus on API and source/config review.
- Certificate pinning bypass is lab-only and only for owned apps/devices.
- Do not intercept or modify traffic for third-party users.

### Language-Specific

PlannerAgent should select language/framework tests from detected stack:

- Python: Flask, Django, FastAPI, SQLAlchemy, Jinja, Celery.
- JavaScript/TypeScript: Express, Next.js, NestJS, React, Node package scripts.
- Java: Spring Security, Actuator, JDBC, deserialization surfaces.
- PHP: Laravel middleware, mass assignment, upload handling.
- Ruby: Rails strong parameters, ActiveRecord, secrets config.
- Go: net/http handlers, templates, path joins, SQL construction.

### Whitebox

- Source-to-sink analysis.
- Route authorization mapping.
- Sensitive config review.
- Dependency and secret detection.
- Framework-specific dangerous API usage.

### Blackbox

- Headers, cookies, CORS.
- Auth flow behavior.
- Access-control checks with test accounts.
- Safe canary payloads.
- Runtime error and metadata leakage.

## Safety Classification

Each test must be classified:

- `passive`: no network mutation; static or metadata-only.
- `safe-active`: low-impact, scoped validation with canaries and limits.
- `lab-validation`: controlled exploit validation against explicitly lab-marked targets.
- `blocked`: not supported by Bug Hunter CLI.

Examples:

- Real malware upload: `blocked`.
- Benign malware-control upload test file: `safe-active` or `lab-validation` depending on target.
- Real ZIP bomb: `blocked`.
- Archive parser static review: `passive`.
- Controlled archive expansion limit test in local lab: `lab-validation`.
- Password spraying: `blocked`.
- Auth lockout configuration review: `passive`.

