"""
NexaVigil - Correlation Pre-Filter
Deterministic + LLM filtering before expensive Gemini 3.5 Flash calls.
"""
from datetime import datetime, timedelta
from typing import List, Tuple, Dict
from connectors.gemma_filter import llm_pre_filter as pre_filter
import json


def parse_time(time_str: str) -> datetime:
    """Parse ISO timestamp string, handling both aware and naive."""
    dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    # Convert to naive UTC for comparison
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt


def find_candidate_pairs(odds_events: List[Dict], 
                         equity_signals: List[Dict],
                         window_hours: int = 72) -> List[Tuple[Dict, Dict, float, str]]:
    """
    Find candidate pairs within time window.
    For hackathon: pass ALL pairs in window to Gemini (LLM filter is advisory only).
    """
    pairs = []
    
    for oe in odds_events:
        oe_time = parse_time(oe["timestamp"])
        
        for es in equity_signals:
            date_field = "disclosed_date" if es.get("filer_type") == "congress" else "filing_date"
            es_date_str = es.get(date_field, es.get("filing_date", "2026-08-01"))
            
            try:
                es_time = datetime.strptime(es_date_str, "%Y-%m-%d")
            except ValueError:
                continue
            
            time_diff = abs((oe_time - es_time).total_seconds() / 3600)
            
            if time_diff <= window_hours:
                # Run LLM pre-filter (advisory - log result but don't block)
                is_related, reason = pre_filter(oe, es)
                
                # For demo: include ALL pairs in window, note LLM opinion
                pairs.append((oe, es, time_diff, f"LLM: {'YES' if is_related else 'NO'} - {reason}"))
                print(f"  ✓ Candidate: {oe['fixture_id']} ↔ {es['ticker']} "
                      f"(Δ{time_diff:.1f}h) - LLM: {'YES' if is_related else 'NO'}")
    
    return pairs


if __name__ == "__main__":
    # Test with sample data
    from google.cloud import firestore
    db = firestore.Client()
    
    odds = [d.to_dict() for d in db.collection("odds_events").limit(10).stream()]
    equity = [d.to_dict() for d in db.collection("equity_signals").limit(10).stream()]
    
    print(f"Found {len(odds)} odds events, {len(equity)} equity signals")
    pairs = find_candidate_pairs(odds, equity)
    print(f"\nCandidate pairs: {len(pairs)}")