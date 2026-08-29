import json, logging
from datetime import datetime
from agents.correlation_reasoner.reasoner import score_pair
from agents.skeptic.agent import skeptic_review
from agents.case_memory.agent import create_case

BANNED_WORDS = ["confirmed", "guilty", "proven", "definitely insider", "insider trading occurred"]
REQUIRED_KEYS = {"convergence_score", "reasoning_chain", "evidence_list", "confidence", "recommended_action"}

def validate_result(result: dict):
    if not REQUIRED_KEYS.issubset(result.keys()):
        raise KeyError(f"missing fields: {REQUIRED_KEYS - result.keys()}")
    text = " ".join(result.get("reasoning_chain", [])) + " " + result.get("recommended_action", "")
    if any(w in text.lower() for w in BANNED_WORDS):
        raise ValueError("banned accusatory language detected")

def log_decision(odds_event, equity_signal, result, case_id=None, error=None):
    log = {
        "event": "correlation_decision",
        "odds_event_id": odds_event.get("fixture_id"),
        "equity_signal_ticker": equity_signal.get("ticker"),
        "convergence_score": result.get("convergence_score") if result else None,
        "model": "gemini-3.5-flash",
        "skeptic_model": "newsapi_heuristic",
        "timestamp": datetime.utcnow().isoformat(),
        "case_id": case_id,
        "error": str(error) if error else None
    }
    logging.info(json.dumps(log))

def run_pipeline_cycle():
    pass  # TODO: wire full pipeline
