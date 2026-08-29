from google.cloud import firestore
from datetime import datetime

db = firestore.Client()

def create_case(odds_event, equity_signal, correlation_result, skeptic_result):
    cs = correlation_result.get("convergence_score", 0)
    ss = skeptic_result.get("skeptic_score", 100)
    if cs >= 60 and ss < 30:
        case = {
            "odds_event": odds_event,
            "equity_signal": equity_signal,
            "convergence_score": cs,
            "skeptic_score": ss,
            "alternative_explanations": skeptic_result.get("alternative_explanations", []),
            "reasoning_chain": correlation_result.get("reasoning_chain", []),
            "evidence_list": correlation_result.get("evidence_list", []),
            "confidence": correlation_result.get("confidence", "low"),
            "recommended_action": correlation_result.get("recommended_action", "requires human review"),
            "status": "open",
            "officer_feedback": {},
            "created_at": datetime.utcnow().isoformat()
        }
        ref = db.collection("cases").add(case)
        return ref[1].id
    return None
