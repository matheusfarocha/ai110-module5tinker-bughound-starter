# BugHound Mini Model Card

---

## 1) What is this system?

**Name:** BugHound
**Purpose:** Scans Python code for bugs, suggests fixes, and checks if those fixes are safe to apply automatically.
**Intended users:** Students learning how AI agents make decisions about code.

---

## 2) How does it work?

BugHound follows five steps:

1. **Plan** — Decides to scan the code and propose a fix.
2. **Analyze** — Looks for problems. If an AI model (Gemini) is available, it asks the AI. If not, it uses built-in pattern matching (heuristics) to find common issues like `print()` statements, bare `except:` blocks, and `TODO` comments.
3. **Act** — Proposes a rewritten version of the code that addresses the issues found.
4. **Test** — Scores how risky the fix is (0-100). Checks things like: did the fix remove too many lines? Did it delete return statements? Each issue's severity and confidence level affects the score.
5. **Reflect** — If the risk score is 75 or above, the fix is considered safe to auto-apply. Otherwise, it flags the fix for human review.

Heuristics handle steps 2-3 offline. Gemini handles them when an API key is set.

---

## 3) Inputs and outputs

**Inputs:**
- Short Python functions and scripts (5-20 lines)
- Tested with: clean code (`cleanish.py`), code with multiple issues (`mixed_issues.py`), and edge cases like empty files

**Outputs:**
- A list of detected issues, each with a type, severity, confidence score, and description
- A rewritten version of the code with fixes applied
- A risk report with a numeric score, risk level (low/medium/high), and an autofix recommendation

---

## 4) Reliability and safety rules

**Rule 1: Severity-weighted penalty**
- Checks each issue's severity (High = -40, Medium = -20, Low = -5), scaled by confidence
- Matters because a high-severity bug like a bare `except:` is more dangerous than a stray `print()`
- False positive: the LLM labels something "High" that is actually harmless
- False negative: a serious bug gets labeled "Low" and barely affects the score

**Rule 2: Code length reduction check**
- Penalizes fixes that are much shorter than the original, scaled by how much was removed
- Matters because a fix that deletes most of the code probably broke something
- False positive: a valid refactor that simplifies verbose code gets penalized
- False negative: a fix that replaces correct logic with wrong logic of the same length passes undetected

---

## 5) Observed failure modes

**1. Missed issue:** An empty file produces zero issues and a score of 0. BugHound says "no fix produced" but doesn't warn that the input itself was invalid. It treats empty input the same as unfixable code.

**2. Silent penalty skip:** When Gemini returns a non-standard severity like "Critical" instead of "High", the risk assessor used to skip the penalty entirely. The issue appeared in the UI but had zero effect on the risk score. We fixed this by adding a default -15 penalty for unknown severities.

---

## 6) Heuristic vs Gemini comparison

- **Gemini detected** logic errors, naming issues, and security concerns that pattern matching cannot catch
- **Heuristics caught** `print()`, bare `except:`, and `TODO` every time — simple but consistent
- **Fixes differed:** heuristic fixes are mechanical (swap `print` for `logging.info`). Gemini rewrites are more context-aware but occasionally change behavior in unexpected ways
- **Risk scorer** sometimes disagreed with intuition — a clearly better Gemini fix could score lower than a heuristic fix because it changed more lines

---

## 7) Human-in-the-loop decision

**Scenario:** The fix removes or changes a `return` statement.

- **Trigger:** If the original code has a `return` and the fixed code changes what gets returned (not just removing it entirely, which is already caught)
- **Where:** In `risk_assessor.py`, as a new structural check
- **Message:** "This fix modifies return values. Auto-apply is disabled — please verify the output is still correct."

---

## 8) Improvement idea

Add a guardrail that compares function signatures before and after the fix. If the fix changes parameter names, adds new parameters, or removes existing ones, flag it as high risk. This catches a common AI mistake (rewriting a function's interface) with a simple string comparison, no AI needed.
