# ContextManagerAgent

## Identity

**Name**: ContextManagerAgent  
**Role**: Context window management, token budget enforcement, snippet selection, and cost tracking  
**Phase**: Active throughout the full pipeline — consulted before every LLM call  
**LangGraph node**: Utility node called by other agents, not a standalone pipeline step  

---

## Purpose

ContextManagerAgent solves the hardest practical problem in AI-powered code analysis: **large repositories blow up model context windows and API costs instantly** if you are not disciplined about what you send.

Bug Hunter CLI's index-first design already prevents sending the whole repo to the model. ContextManagerAgent enforces this discipline systematically. Every agent that wants to make an LLM call must go through ContextManagerAgent to:

1. Check the remaining token budget for the current run.
2. Select the most relevant snippets from the index (not the whole index).
3. Chunk large evidence packets into model-safe sizes.
4. Track token usage per run, per agent, and per test.
5. Cache index entries and summaries to avoid redundant calls.

---

## Token Budget System

Each run has a configurable token budget defined in `bughunter-scope.yml`:

```yaml
cost:
  max_tokens_per_run: 500000      # hard limit
  max_tokens_per_test: 20000      # per test plan
  max_cost_usd: 2.00              # soft warning at 80%, hard stop at 100%
  warn_at_percent: 80
```

**Default budgets** (if not configured):
- Max tokens per run: 200,000
- Max tokens per test: 15,000
- Max cost USD: $1.00

When the budget reaches 80%, the TUI shows a warning in the Score Summary panel. When it reaches 100%, active LLM calls are blocked and the run switches to deterministic-only mode, completing what it can without further model calls.

---

## Snippet Selection

Before any agent sends a code snippet to the LLM, it calls `ContextManagerAgent.select_snippets(tags, max_tokens)`:

### Selection Algorithm

1. **Tag matching**: Look up index entries matching the requested tags (e.g., `["sql", "auth"]`).
2. **Relevance scoring**: Rank entries by:
   - Tag overlap with test category
   - Security relevance score from index
   - File risk score (auth > config > general)
   - Recently accessed entries get a small penalty (avoid repeating the same file)
3. **Token budget check**: Estimate token count for each entry (approx 4 chars per token).
4. **Greedy selection**: Select entries in rank order until the `max_tokens` budget is consumed.
5. **Snippet extraction**: For each selected entry, extract the exact line range from the file. Do not send the whole file.

### Snippet Format

```
File: auth/views.py  (Lines 138-155)
Tags: [sql, auth, injection]
Security relevance: HIGH
---
def login(request):
    user_id = request.POST.get('user_id')
    result = db.execute(f"SELECT * FROM users WHERE id = {user_id}")  # line 142
    ...
---
Why selected: Matches 'sql' tag; contains string-formatted query construction at line 142.
```

---

## Context Window Strategy

### Per-Call Limits

| Agent | Max tokens per call |
|---|---|
| ReconAgent (summarization) | 8,000 |
| StaticAuditAgent (per snippet) | 12,000 |
| DynamicTestAgent (per test) | 10,000 |
| VulnScoringAgent (per finding) | 5,000 |
| FixAgent (per finding) | 8,000 |
| ReportAgent (per section) | 15,000 |

### Chunking Strategy

When an evidence packet exceeds the per-call limit:

1. Split into chunks by logical boundary (function boundary > class boundary > file boundary > line count).
2. Each chunk is sent as a separate LLM call.
3. Results are merged by EvidenceAgent before scoring.
4. Chunk metadata is stored so the report can cite exact ranges.

### Caching

ContextManagerAgent maintains an in-memory + SQLite cache:

- **Index summary cache**: If `index.md` summary was sent to the model in a prior call, the cached summary is reused. TTL: full run lifetime.
- **File summary cache**: If a file was already summarized in this run, reuse the summary instead of re-sending the snippet.
- **Finding dedup cache**: If an identical evidence packet has already been evaluated, skip the LLM call and reuse the prior result.

Cache hits are logged as `cache_hit` events and reduce token usage significantly on repositories with repeated patterns.

---

## Cost Tracking

ContextManagerAgent tracks all LLM API usage:

```sql
CREATE TABLE provider_usage (
    id           TEXT PRIMARY KEY,
    run_id       TEXT NOT NULL,
    agent        TEXT NOT NULL,
    test_id      TEXT,
    model        TEXT NOT NULL,
    prompt_tokens    INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens     INTEGER NOT NULL,
    estimated_cost_usd REAL NOT NULL,
    cached           INTEGER DEFAULT 0,
    called_at        TEXT NOT NULL
);
```

**Cost estimation**:
- Prices are stored in a local config file that the user can update.
- Default prices are set at tool install time for the configured provider.
- Cost estimates are clearly marked as estimates in the TUI and report (exact billing depends on provider).

**TUI display** (Score Summary panel):
```
Tokens: 12,440 / 200,000
Cost:  ~$0.04  (est.)
Budget: OK  ██░░░░░░░░  6%
```

---

## Large Repository Handling

For repositories with more than 1,000 files:

1. ContextManagerAgent applies aggressive pre-filtering before index construction:
   - Ignore all files in excluded directories (`.git`, `node_modules`, `dist`, `.venv`, etc.)
   - Ignore binary, media, and generated files
   - Ignore lock files unless dependency scanning is active
2. File relevance scoring assigns a score (0.0–1.0) to each file based on:
   - Presence of security-relevant symbols in file name
   - File extension and type
   - Presence in known framework patterns (e.g., `views.py`, `routes.js`, `middleware/`)
3. Only files with relevance score above the threshold (default 0.3) are included in the index.
4. The threshold is configurable and is listed in the run record for transparency.

---

## Integration with Other Agents

```
ReconAgent → "I want to summarize these 50 files"
                │
                ▼
        ContextManagerAgent.select_snippets(tags, max_tokens=8000)
                │
                ▼
        Returns: ranked snippet list (≤8000 tokens)
                │
                ▼
        ReconAgent → sends to LLM → gets summary → writes to index.md

StaticAuditAgent → "I want to audit auth/views.py for SQL injection"
                │
                ▼
        ContextManagerAgent.check_budget(agent="static_audit", estimated_tokens=4000)
                │
                ▼
        Budget OK → proceed
        Budget at limit → switch to deterministic-only, skip LLM
```

---

## Failure Handling

- If budget is exhausted mid-run, ContextManagerAgent emits `budget_exhausted` event.
- Remaining tests switch to deterministic-only mode.
- The final report notes which tests were limited by budget.
- The user can increase the budget and resume the run.
