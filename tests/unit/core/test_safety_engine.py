import pytest
from bughunter.core.safety.engine import SafetyPolicyEngine
from bughunter.models.scope import Scope, ScopeProject, Target
from bughunter.models.policy import PolicyAction, PolicyDecisionEnum

@pytest.fixture
def test_scope():
    return Scope(
        project=ScopeProject(name="test"),
        targets=Target(
            urls=["http://localhost:8000", "https://api.example.com"],
            hosts=["db.internal"]
        )
    )

def test_network_request_in_scope_url(test_scope):
    engine = SafetyPolicyEngine(test_scope)
    decision = engine.check("run-1", PolicyAction.network_request, "http://localhost:8000/api/users")
    assert decision.decision == PolicyDecisionEnum.allow

def test_network_request_out_of_scope_url(test_scope):
    engine = SafetyPolicyEngine(test_scope)
    decision = engine.check("run-1", PolicyAction.network_request, "http://evil.com/api/users")
    assert decision.decision == PolicyDecisionEnum.block
    assert "not in scope" in decision.reason

def test_network_request_in_scope_host(test_scope):
    engine = SafetyPolicyEngine(test_scope)
    decision = engine.check("run-1", PolicyAction.network_request, "postgres://db.internal:5432/test")
    assert decision.decision == PolicyDecisionEnum.allow
