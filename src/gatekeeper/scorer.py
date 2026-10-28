"""Layer 2: turn signals into a score and a decision band."""

PASS_MAX = 2    # 0-2   -> pass, no LLM call
BLOCK_MIN = 7   # 7+    -> block directly (no LLM needed)
                # 3-6   -> unsure: send to layer 3 (LLM check)


def total_score(signals) -> int:
    return sum(s.points for s in signals)


def band(score: int) -> str:
    if score <= PASS_MAX:
        return "pass"
    if score >= BLOCK_MIN:
        return "block"
    return "check"
