from reliability.risk_assessor import assess_risk


def test_no_fix_is_high_risk():
    risk = assess_risk(
        original_code="print('hi')\n",
        fixed_code="",
        issues=[{"type": "Code Quality", "severity": "Low", "msg": "print"}],
    )
    assert risk["level"] == "high"
    assert risk["should_autofix"] is False
    assert risk["score"] == 0


def test_low_risk_when_minimal_change_and_low_severity():
    original = "import logging\n\ndef add(a, b):\n    return a + b\n"
    fixed = "import logging\n\ndef add(a, b):\n    return a + b\n"
    risk = assess_risk(
        original_code=original,
        fixed_code=fixed,
        issues=[{"type": "Code Quality", "severity": "Low", "msg": "minor"}],
    )
    assert risk["level"] in ("low", "medium")  # depends on scoring rules
    assert 0 <= risk["score"] <= 100


def test_high_severity_issue_drives_score_down():
    original = "def f():\n    try:\n        return 1\n    except:\n        return 0\n"
    fixed = "def f():\n    try:\n        return 1\n    except Exception as e:\n        return 0\n"
    risk = assess_risk(
        original_code=original,
        fixed_code=fixed,
        issues=[{"type": "Reliability", "severity": "High", "msg": "bare except"}],
    )
    assert risk["score"] <= 60
    assert risk["level"] in ("medium", "high")


def test_confidence_reduces_penalty():
    original = "def f():\n    print('hi')\n    return True\n"
    fixed = "import logging\n\ndef f():\n    logging.info('hi')\n    return True\n"

    full = assess_risk(
        original_code=original,
        fixed_code=fixed,
        issues=[{"type": "Code Quality", "severity": "Low", "msg": "print", "confidence": 1.0}],
    )
    half = assess_risk(
        original_code=original,
        fixed_code=fixed,
        issues=[{"type": "Code Quality", "severity": "Low", "msg": "print", "confidence": 0.5}],
    )
    assert half["score"] >= full["score"]


def test_length_penalty_scales_with_reduction():
    original = "line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10\n"

    mild_cut = "line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\n"  # 80% kept
    severe_cut = "line1\nline2\n"  # 20% kept

    mild = assess_risk(original_code=original, fixed_code=mild_cut, issues=[])
    severe = assess_risk(original_code=original, fixed_code=severe_cut, issues=[])

    assert severe["score"] < mild["score"]


def test_unknown_severity_still_penalizes():
    original = "def f():\n    return 1\n"
    fixed = "def f():\n    return 1\n"
    risk = assess_risk(
        original_code=original,
        fixed_code=fixed,
        issues=[{"type": "Issue", "severity": "Critical", "msg": "LLM said critical"}],
    )
    assert risk["score"] < 100
    assert any("Unknown severity" in r for r in risk["reasons"])


def test_missing_return_is_penalized():
    original = "def f(x):\n    return x + 1\n"
    fixed = "def f(x):\n    x + 1\n"
    risk = assess_risk(
        original_code=original,
        fixed_code=fixed,
        issues=[],
    )
    assert risk["score"] < 100
    assert any("Return" in r or "return" in r for r in risk["reasons"])
