from typing import Any, Dict, List


def assess_risk(
    original_code: str,
    fixed_code: str,
    issues: List[Dict[str, Any]],
) -> Dict[str, object]:
    """
    Simple, explicit risk assessment used as a guardrail layer.

    Returns a dict with:
    - score: int from 0 to 100
    - level: "low" | "medium" | "high"
    - reasons: list of strings explaining deductions
    - should_autofix: bool
    """

    reasons: List[str] = []
    score = 100

    if not fixed_code.strip():
        return {
            "score": 0,
            "level": "high",
            "reasons": ["No fix was produced."],
            "should_autofix": False,
        }

    original_lines = original_code.strip().splitlines()
    fixed_lines = fixed_code.strip().splitlines()

    # ----------------------------
    # Issue severity based risk
    # ----------------------------
    for issue in issues:
        severity = str(issue.get("severity", "")).lower()
        confidence = float(issue.get("confidence", 1.0))

        if severity == "high":
            score -= int(40 * confidence)
            reasons.append(f"High severity issue detected (confidence: {confidence:.0%}).")
        elif severity == "medium":
            score -= int(20 * confidence)
            reasons.append(f"Medium severity issue detected (confidence: {confidence:.0%}).")
        elif severity == "low":
            score -= int(5 * confidence)
            reasons.append(f"Low severity issue detected (confidence: {confidence:.0%}).")
        else:
            score -= int(15 * confidence)
            reasons.append(f"Unknown severity '{severity}' treated as medium (confidence: {confidence:.0%}).")

    # ----------------------------
    # Structural change checks
    # ----------------------------
    if original_lines:
        ratio = len(fixed_lines) / len(original_lines)
        if ratio < 0.8:
            penalty = min(30, int((1 - ratio) * 35))
            score -= penalty
            reasons.append(f"Fixed code is {1 - ratio:.0%} shorter than original (−{penalty}).")

    if "return" in original_code and "return" not in fixed_code:
        score -= 30
        reasons.append("Return statements may have been removed.")

    if "except:" in original_code and "except:" not in fixed_code:
        # This is usually good, but still risky.
        score -= 5
        reasons.append("Bare except was modified, verify correctness.")

    # ----------------------------
    # Clamp score
    # ----------------------------
    score = max(0, min(100, score))

    # ----------------------------
    # Risk level
    # ----------------------------
    if score >= 75:
        level = "low"
    elif score >= 40:
        level = "medium"
    else:
        level = "high"

    # ----------------------------
    # Auto-fix policy
    # ----------------------------
    should_autofix = level == "low"

    if not reasons:
        reasons.append("No significant risks detected.")

    return {
        "score": score,
        "level": level,
        "reasons": reasons,
        "should_autofix": should_autofix,
    }
