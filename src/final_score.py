FORMULA = "final_score = 0.70 * rule_based_score + 0.30 * ai_review_score"


def calculate_final_score(rule_based_score, ai_review_score):
    final_score = round((0.70 * rule_based_score) + (0.30 * ai_review_score), 2)
    decision = "ready_for_generation" if final_score >= 90 else "needs_improvement"
    return {
        "rule_based_score": rule_based_score,
        "ai_review_score": ai_review_score,
        "final_score": final_score,
        "decision": decision,
        "formula": FORMULA,
    }
