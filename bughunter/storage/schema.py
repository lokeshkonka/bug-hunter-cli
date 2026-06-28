INITIAL_SCHEMA = """
-- Core run tracking
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    status TEXT,
    scope_path TEXT,
    created_at TEXT,
    completed_at TEXT,
    token_budget INTEGER,
    cost_budget_usd REAL
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    type TEXT,
    agent TEXT,
    message TEXT,
    metadata TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS targets (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    url TEXT,
    host TEXT,
    scope_mode TEXT
);

CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    path TEXT,
    language TEXT,
    relevance_score REAL,
    excluded INTEGER,
    excluded_reason TEXT
);

-- Index
CREATE TABLE IF NOT EXISTS index_entries (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    file_id TEXT,
    symbol TEXT,
    line_start INTEGER,
    line_end INTEGER,
    security_relevance TEXT,
    tags TEXT,
    test_category TEXT,
    semgrep_rule_ids TEXT
);

-- Tests
CREATE TABLE IF NOT EXISTS test_plans (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    title TEXT,
    category TEXT,
    safety_class TEXT,
    target TEXT,
    plan_path TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS test_results (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    test_plan_id TEXT,
    status TEXT,
    tools_run TEXT,
    evidence_ids TEXT,
    finding_ids TEXT,
    created_at TEXT
);

-- Safety
CREATE TABLE IF NOT EXISTS policy_decisions (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    action TEXT,
    target TEXT,
    decision TEXT,
    reason TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS policy_violations (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    action TEXT,
    target TEXT,
    reason TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS security_events (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    event_type TEXT,
    source_file TEXT,
    source_line INTEGER,
    pattern TEXT,
    confidence TEXT,
    content_hash TEXT,
    detected_at TEXT,
    action_taken TEXT
);

-- Evidence and findings
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    test_plan_id TEXT,
    source_tool TEXT,
    source_file TEXT,
    line_start INTEGER,
    line_end INTEGER,
    observation TEXT,
    metadata TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    title TEXT,
    severity TEXT,
    confidence TEXT,
    category TEXT,
    affected_component TEXT,
    evidence_ids TEXT,
    impact TEXT,
    reproduction_steps TEXT,
    recommendation TEXT,
    retest_steps TEXT,
    status TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS score_components (
    id TEXT PRIMARY KEY,
    finding_id TEXT,
    run_id TEXT,
    cvss_score REAL,
    confidence_score REAL,
    exploitability_score REAL,
    remediation_score REAL,
    evidence_weight REAL,
    composite_score REAL,
    risk_tier TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS provider_usage (
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
"""
