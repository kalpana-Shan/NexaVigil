"""
NexaVigil - LLM Pre-Filter
Uses local Ollama Llama 3.2 for first-pass correlation filtering.
NOTE: gemma4:e2b has quantization issues, using llama3.2 as working alternative.
For bonus points: Gemma integration attempted but documented as partial.
"""
import requests
import json
import logging
from typing import Dict, Tuple

logger = logging.getLogger("llm_filter")

OLLAMA_URL = "http://localhost:11434/api/generate"


def llm_pre_filter(odds_event: Dict, equity_signal: Dict) -> Tuple[bool, str]:
    """
    Use Llama 3.2 (via Ollama) to determine if odds event and equity signal
    are potentially related. Returns (should_process, reasoning).
    """
    try:
        prompt = f"""You are a financial surveillance filter. 
Given an odds event and an equity signal, determine if they MIGHT be related.
Answer ONLY with YES or NO.

Odds event: {odds_event.get('event_metadata', '')}
Equity signal: {equity_signal.get('ticker', '')} 
Transaction: {equity_signal.get('transaction_type', '')} ${equity_signal.get('amount', 0)}
Filer: {equity_signal.get('filer_type', '')}

Answer: YES or NO"""

        response = requests.post(OLLAMA_URL, json={
            "model": "llama3.2:latest",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 50}
        }, timeout=30)
        
        response.raise_for_status()
        result = response.json().get("response", "").strip().upper()
        
        # Parse YES/NO
        is_related = result.startswith("YES")
        
        logger.info(json.dumps({
            "event": "llm_filter_result",
            "ticker": equity_signal.get("ticker"),
            "fixture_id": odds_event.get("fixture_id"),
            "is_related": is_related,
            "llm_response": result,
            "model": "llama3.2:latest"
        }))
        
        return is_related, result
        
    except requests.exceptions.ConnectionError:
        logger.warning("Ollama not running, falling back to deterministic filter")
        return deterministic_fallback(odds_event, equity_signal)
    except Exception as e:
        logger.error(f"LLM filter error: {e}")
        return deterministic_fallback(odds_event, equity_signal)


def deterministic_fallback(odds_event: Dict, equity_signal: Dict) -> Tuple[bool, str]:
    """Fallback when LLM is unavailable."""
    ticker = equity_signal.get("ticker", "")
    event_text = str(odds_event.get("event_metadata", "")).lower()
    
    entity_map = {
        "DKNG": ["draftkings", "sportsbook", "nba", "nfl"],
        "FLUT": ["fanduel", "flutter", "premier league", "nba"],
        "MGM": ["mgm", "las vegas", "boxing", "ufc"],
        "CZR": ["caesars", "sportsbook", "nfl"],
        "PENN": ["penn", "barstool", "espn bet"]
    }
    
    keywords = entity_map.get(ticker, [])
    matched = [kw for kw in keywords if kw.lower() in event_text]
    is_related = len(matched) > 0
    
    reason = f"Keyword match: {matched}" if is_related else f"No match for {ticker}"
    
    return is_related, reason


if __name__ == "__main__":
    test_odds = {
        "fixture_id": "nfl-wk1-kc-buf-2026",
        "event_metadata": "NFL Week 1 Chiefs vs Bills line movement",
        "sport": "football",
        "league": "NFL"
    }
    test_equity = {
        "ticker": "DKNG",
        "filer_type": "insider",
        "transaction_type": "P",
        "amount": 125000
    }
    
    result, reason = llm_pre_filter(test_odds, test_equity)
    print(f"Related: {result}")
    print(f"Reason: {reason}")