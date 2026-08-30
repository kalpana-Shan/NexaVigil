"""
NexaVigil - Supervisor Agent
Orchestrates all sub-agents: Odds Sentinel, Equity Pulse, Correlation Reasoner, Skeptic, Case Memory.
Routes events, enforces retry logic, validates outputs, prevents infinite loops.
"""
import os
import json
import logging
import uuid
from typing import Dict, Optional
from datetime import datetime, timezone

# Import all agents
from agents.correlation_reasoner.reasoner import score_pair
from agents.skeptic.skeptic import skeptic_review
from agents.case_memory.case_memory import create_case

logger = logging.getLogger("supervisor")

# Validation rules from hackathon plan
BANNED_WORDS = ['confirmed', 'guilty', 'proven', 'definitely insider', 'caught', 'red-handed']
REQUIRED_CORR_KEYS = {'convergence_score', 'reasoning_chain', 'evidence_list', 'confidence', 'recommended_action'}
MAX_RETRIES = 2


def validate_correlation_result(result: Dict) -> Dict:
    """Validate Correlation Reasoner output."""
    if not REQUIRED_CORR_KEYS.issubset(result.keys()):
        missing = REQUIRED_CORR_KEYS - result.keys()
        raise KeyError(f"Missing fields: {missing}")
    
    text = " ".join(result.get('reasoning_chain', [])) + " " + result.get('recommended_action', '')
    if any(w in text.lower() for w in BANNED_WORDS):
        raise ValueError("Banned accusatory language detected")
    
    if result.get('recommended_action') != 'requires human review':
        raise ValueError("recommended_action must be 'requires human review'")
    
    result['convergence_score'] = int(result['convergence_score'])
    return result


def score_pair_with_retry(odds_event: Dict, equity_signal: Dict, time_diff_hours: float) -> Optional[Dict]:
    """Call Correlation Reasoner with retry-once logic."""
    for attempt in range(MAX_RETRIES):
        try:
            result = score_pair(odds_event, equity_signal, time_diff_hours)
            return validate_correlation_result(result)
        except Exception as e:
            logger.warning(f"Correlation attempt {attempt + 1} failed: {e}")
            if attempt == MAX_RETRIES - 1:
                logger.error(f"Correlation failed after {MAX_RETRIES} attempts")
                return None
    return None


def compute_time_diff(odds_event: Dict, equity_signal: Dict) -> float:
    """Compute time difference in hours between odds event and equity signal."""
    from datetime import datetime
    odds_time = datetime.fromisoformat(odds_event.get("timestamp", "").replace("Z", "+00:00"))
    equity_time = datetime.fromisoformat(equity_signal.get("filing_date", "").replace("Z", "+00:00"))
    diff = abs((odds_time - equity_time).total_seconds() / 3600)
    return diff


def generate_case_id() -> str:
    """Generate unique case ID."""
    return f"case-{uuid.uuid4().hex[:8]}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def evaluate_pair(odds_event: Dict, equity_signal: Dict) -> Dict:
    """
    Main orchestration flow:
    1. Correlation Reasoner scores the pair
    2. If score >= 60, Skeptic Agent debunks
    3. If skeptic_score < 30, create Case in Firestore
    """
    logger.info(json.dumps({
        "event": "evaluation_started",
        "fixture_id": odds_event.get("fixture_id"),
        "ticker": equity_signal.get("ticker"),
    }))
    
    # Step 1: Compute time diff
    try:
        time_diff = compute_time_diff(odds_event, equity_signal)
    except Exception as e:
        logger.error(f"Time diff computation failed: {e}")
        return {"status": "failed", "reason": "time_diff_error"}
    
    # Step 2: Correlation Reasoner with retry
    corr_result = score_pair_with_retry(odds_event, equity_signal, time_diff)
    if corr_result is None:
        return {"status": "failed", "reason": "correlation_failed"}
    
    convergence_score = corr_result["convergence_score"]
    logger.info(f"Convergence score: {convergence_score}")
    
    # Step 3: Gate - only high correlation goes to Skeptic
    if convergence_score < 60:
        return {
            "status": "filtered",
            "reason": "low_correlation",
            "convergence_score": convergence_score,
        }
    
    # Step 4: Skeptic Agent
    try:
        skeptic_result = skeptic_review(odds_event, equity_signal, time_diff)
        skeptic_score = skeptic_result["skeptic_score"]
    except Exception as e:
        logger.error(f"Skeptic failed: {e}")
        return {
            "status": "failed",
            "reason": "skeptic_failed",
            "convergence_score": convergence_score,
        }
    
    logger.info(f"Skeptic score: {skeptic_score}")
    
    # Step 5: Gate - only low skeptic score creates case
    if skeptic_score >= 30:
        return {
            "status": "filtered",
            "reason": "skeptic_debunked",
            "convergence_score": convergence_score,
            "skeptic_score": skeptic_score,
            "alternative_explanations": skeptic_result.get("alternative_explanations", []),
        }
    
    # Step 6: Create Case
    try:
        case_id = generate_case_id()
        case = create_case(
            case_id=case_id,
            odds_event=odds_event,
            equity_signal=equity_signal,
            correlation_result=corr_result,
            skeptic_result=skeptic_result,
            time_diff_hours=time_diff,
        )
        return {
            "status": "case_created",
            "case_id": case_id,
            "convergence_score": convergence_score,
            "skeptic_score": skeptic_score,
            "case": case,
        }
    except Exception as e:
        logger.error(f"Case creation failed: {e}")
        return {
            "status": "failed",
            "reason": "case_creation_failed",
            "convergence_score": convergence_score,
            "skeptic_score": skeptic_score,
        }


if __name__ == "__main__":
    # End-to-end test
    test_odds = {
        "fixture_id": "nfl-wk1-kc-buf-2026",
        "sport": "football",
        "league": "NFL",
        "market": "moneyline",
        "sportsbook": "kalshi",
        "pct_move": 0.1262,
        "timestamp": "2026-08-29T10:00:00Z",
        "event_metadata": "Sharp 12.6% move on NFL Week 1 Chiefs vs Bills at Kalshi"
    }
    test_equity = {
        "ticker": "DKNG",
        "filer_name": "Jason Robins",
        "filer_type": "insider",
        "transaction_type": "P",
        "amount": 125000,
        "filing_date": "2026-08-29",
        "disclosed_date": "2026-08-29",
        "signal_type": "form4"
    }
    
    result = evaluate_pair(test_odds, test_equity)
    print(json.dumps(result, indent=2))