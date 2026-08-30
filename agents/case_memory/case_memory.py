"""
NexaVigil - Case Memory Agent
Persists cases to Firestore and handles officer feedback.
"""
import os
import json
import logging
from typing import Dict, Optional
from datetime import datetime, timezone
from google.cloud import firestore

logger = logging.getLogger("case_memory")

db = firestore.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT", "nexavigil"))

CASES_COLLECTION = "confluence_cases"
OFFICER_PREFS_COLLECTION = "confluence_officer_preferences"


def create_case(
    case_id: str,
    odds_event: Dict,
    equity_signal: Dict,
    correlation_result: Dict,
    skeptic_result: Dict,
    time_diff_hours: float,
) -> Dict:
    """
    Create a new case in Firestore when correlation_score >= 60 and skeptic_score < 30.
    """
    case = {
        "case_id": case_id,
        "odds_event_ref": odds_event.get("fixture_id"),
        "equity_signal_ref": equity_signal.get("ticker"),
        "convergence_score": correlation_result.get("convergence_score"),
        "skeptic_score": skeptic_result.get("skeptic_score"),
        "alternative_explanations": skeptic_result.get("alternative_explanations", []),
        "reasoning_chain": correlation_result.get("reasoning_chain", []),
        "evidence_list": correlation_result.get("evidence_list", []),
        "confidence": correlation_result.get("confidence"),
        "recommended_action": correlation_result.get("recommended_action"),
        "status": "open",  # open | approved | rejected | false_positive
        "officer_feedback": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    db.collection(CASES_COLLECTION).document(case_id).set(case)
    logger.info(f"Case created: {case_id}")
    return case


def get_case(case_id: str) -> Optional[Dict]:
    """Retrieve a case by ID."""
    doc = db.collection(CASES_COLLECTION).document(case_id).get()
    if doc.exists:
        return doc.to_dict()
    return None


def list_cases(status: Optional[str] = None, limit: int = 50) -> list:
    """List cases, optionally filtered by status."""
    query = db.collection(CASES_COLLECTION).order_by("created_at", direction=firestore.Query.DESCENDING)
    if status:
        query = query.where("status", "==", status)
    return [doc.to_dict() for doc in query.limit(limit).stream()]


def update_case_feedback(case_id: str, feedback: str, officer_id: str = "maria") -> Dict:
    """
    Officer provides feedback: 'approve', 'reject', or 'false_positive'.
    Adjusts future thresholds based on feedback.
    """
    case_ref = db.collection(CASES_COLLECTION).document(case_id)
    case = case_ref.get().to_dict()

    if not case:
        raise ValueError(f"Case {case_id} not found")

    # Update case
    updates = {
        "status": feedback,
        "officer_feedback": feedback,
        "officer_id": officer_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    case_ref.update(updates)

    # Update officer preferences (collaborative partner layer)
    if feedback == "false_positive":
        _adjust_threshold(officer_id, case["equity_signal_ref"], direction="raise")
    elif feedback == "approve":
        _adjust_threshold(officer_id, case["equity_signal_ref"], direction="lower")

    logger.info(f"Case {case_id} updated with feedback: {feedback}")
    return {**case, **updates}


def _adjust_threshold(officer_id: str, ticker: str, direction: str):
    """Adjust officer's sensitivity threshold based on feedback."""
    prefs_ref = db.collection(OFFICER_PREFS_COLLECTION).document(f"{officer_id}_{ticker}")
    prefs = prefs_ref.get().to_dict() or {
        "officer_id": officer_id,
        "ticker": ticker,
        "false_positive_count": 0,
        "adjusted_threshold": 60,  # default correlation threshold
    }

    if direction == "raise":
        prefs["false_positive_count"] += 1
        prefs["adjusted_threshold"] = min(90, prefs["adjusted_threshold"] + 5)
    else:
        prefs["adjusted_threshold"] = max(30, prefs["adjusted_threshold"] - 2)

    prefs["last_updated"] = datetime.now(timezone.utc).isoformat()
    prefs_ref.set(prefs)


def get_officer_preferences(officer_id: str, ticker: str) -> Dict:
    """Get officer's adjusted threshold for a ticker."""
    doc = db.collection(OFFICER_PREFS_COLLECTION).document(f"{officer_id}_{ticker}").get()
    if doc.exists:
        return doc.to_dict()
    return {
        "officer_id": officer_id,
        "ticker": ticker,
        "false_positive_count": 0,
        "adjusted_threshold": 60,
    }


if __name__ == "__main__":
    # Test
    test_case_id = "test-case-001"
    test_odds = {"fixture_id": "nfl-wk1-kc-buf-2026", "sport": "football"}
    test_equity = {"ticker": "DKNG", "signal_type": "form4"}
    test_corr = {"convergence_score": 75, "reasoning_chain": ["test"], "evidence_list": ["test"], "confidence": "medium", "recommended_action": "requires human review"}
    test_skeptic = {"skeptic_score": 20, "alternative_explanations": ["earnings report"], "sources_checked": ["yahoo finance"], "confidence": "high"}

    case = create_case(test_case_id, test_odds, test_equity, test_corr, test_skeptic, 14.5)
    print("Created:", json.dumps(case, indent=2))

    retrieved = get_case(test_case_id)
    print("Retrieved:", json.dumps(retrieved, indent=2))

    updated = update_case_feedback(test_case_id, "approve")
    print("Updated:", json.dumps(updated, indent=2))