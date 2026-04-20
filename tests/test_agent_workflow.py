import json

from bughound_agent import BugHoundAgent
from llm_client import MockClient


def test_workflow_runs_in_offline_mode_and_returns_shape():
    agent = BugHoundAgent(client=None)  # heuristic-only
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)

    assert isinstance(result, dict)
    assert "issues" in result
    assert "fixed_code" in result
    assert "risk" in result
    assert "logs" in result

    assert isinstance(result["issues"], list)
    assert isinstance(result["fixed_code"], str)
    assert isinstance(result["risk"], dict)
    assert isinstance(result["logs"], list)
    assert len(result["logs"]) > 0


def test_offline_mode_detects_print_issue():
    agent = BugHoundAgent(client=None)
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)

    assert any(issue.get("type") == "Code Quality" for issue in result["issues"])


def test_offline_mode_proposes_logging_fix_for_print():
    agent = BugHoundAgent(client=None)
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)

    fixed = result["fixed_code"]
    assert "logging" in fixed
    assert "logging.info(" in fixed


def test_heuristic_issues_include_confidence():
    agent = BugHoundAgent(client=None)
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)
    for issue in result["issues"]:
        assert "confidence" in issue
        assert 0.0 <= issue["confidence"] <= 1.0


class MockClientUnknownSeverity:
    """Returns valid JSON with non-standard severities the risk assessor doesn't recognize."""

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if "Return ONLY valid JSON" in system_prompt:
            return json.dumps([
                {"type": "Security", "severity": "Critical", "msg": "Possible injection"},
                {"type": "Security", "severity": "Severe", "msg": "Unsafe deserialization"},
            ])
        return "def f():\n    return safe()\n"


def test_unknown_severity_from_llm_still_penalizes_risk():
    agent = BugHoundAgent(client=MockClientUnknownSeverity())
    code = "def f():\n    return user_input\n"
    result = agent.run(code)

    assert len(result["issues"]) == 2
    assert result["issues"][0]["severity"] == "Critical"
    assert result["issues"][1]["severity"] == "Severe"

    # Without the guardrail these unknown severities would score 100 (no penalty).
    # With the guardrail each gets -15, so score <= 70 and autofix is blocked.
    assert result["risk"]["score"] < 75
    assert any("Unknown severity" in r for r in result["risk"]["reasons"])
    assert result["risk"]["should_autofix"] is False


def test_mock_client_forces_llm_fallback_to_heuristics_for_analysis():
    # MockClient returns non-JSON for analyzer prompts, so agent should fall back.
    agent = BugHoundAgent(client=MockClient())
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)

    assert any(issue.get("type") == "Code Quality" for issue in result["issues"])
    # Ensure we logged the fallback path
    assert any("Falling back to heuristics" in entry.get("message", "") for entry in result["logs"])
