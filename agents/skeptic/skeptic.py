"""
NexaVigil - Skeptic Agent
Debunks candidate pairs by finding benign explanations.
Uses Gemini 2.5 Flash via Vertex AI (same as Correlation Reasoner).
PRIMARY INNOVATION: Transforms naive correlator into skeptical analyst team.
"""
import os
import json
import logging
from typing import Dict, List
import vertexai
from vertexai.generative_models import GenerativeModel

logger = logging.getLogger("skeptic")

# Init Vertex AI (same project as Correlation Reasoner)
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "nexavigil")
LOCATION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
vertexai.init(project=PROJECT_ID, location=LOCATION)

MODEL_NAME = "gemini-2.5-flash"
model = GenerativeModel(MODEL_NAME)

SKEPTIC_PROMPT = """You are a skeptical analyst whose job is to DEBUNK suspicious-looking correlations.
Your goal is to find BENIGN (innocent) explanations for why two events might coincide.

CANDIDATE PAIR TO DEBUNK:
ODDS EVENT:
- Sport: {sport}
- League: {league}
- Market: {market}
- Event: {event_metadata}
- Time: {timestamp}

EQUITY SIGNAL:
- Ticker: {ticker}
- Signal Type: {signal_type}
- Filer: {filer_name}
- Transaction: {transaction_type} ${amount:,}
- Date: {filing_date}

TIME GAP: {time_diff:.1f} hours

CHECK FOR THESE BENIGN EXPLANATIONS:
1. Injury reports or player news (especially for sports events)
2. Earnings announcements or scheduled corporate events
3. Weather events (for outdoor sports)
4. General market sentiment or sector-wide moves
5. Public news that could affect both markets
6. Coincidence / random correlation

INSTRUCTIONS:
- Be thorough but concise
- If you find a benign explanation, explain it clearly
- If no benign explanation exists, say so honestly
- Return ONLY valid JSON:

{{
  "skeptic_score": <integer 0-100, 0=fully explained/benign, 100=no explanation found>,
  "alternative_explanations": [<list of strings, each explaining one benign possibility>],
  "sources_checked": [<list of strings describing what you checked>],
  "confidence": "low" | "medium" | "high"
}}

Rules:
- skeptic_score 0-30: Strong benign explanation found
- skeptic_score 31-70: Possible benign explanation, unclear
- skeptic_score 71-100: No benign explanation found, remains suspicious
- Be honest. If something genuinely looks suspicious, say so.
"""


def skeptic_review(odds_event: Dict, equity_signal: Dict, time_diff_hours: float) -> Dict:
    """
    Debunk a candidate pair by finding benign explanations.
    Returns skeptic_score and alternative_explanations.
    """
    prompt = SKEPTIC_PROMPT.format(
        sport=odds_event.get("sport", "unknown"),
        league=odds_event.get("league", "unknown"),
        market=odds_event.get("market", "unknown"),
        event_metadata=odds_event.get("event_metadata", ""),
        timestamp=odds_event.get("timestamp", ""),
        ticker=equity_signal.get("ticker", "UNKNOWN"),
        signal_type=equity_signal.get("signal_type", "unknown"),
        filer_name=equity_signal.get("filer_name", "unknown"),
        transaction_type=equity_signal.get("transaction_type", "unknown"),
        amount=equity_signal.get("amount", 0),
        filing_date=equity_signal.get("filing_date", "N/A"),
        time_diff=time_diff_hours,
    )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Strip markdown fences
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        result = json.loads(text.strip())

        # Validate schema
        required = {"skeptic_score", "alternative_explanations", "sources_checked", "confidence"}
        if not required.issubset(result.keys()):
            missing = required - result.keys()
            raise KeyError(f"Missing fields: {missing}")

        # Normalize
        result["skeptic_score"] = int(result["skeptic_score"])
        result["confidence"] = result["confidence"].lower()

        logger.info(json.dumps({
            "event": "skeptic_reviewed",
            "fixture_id": odds_event.get("fixture_id"),
            "ticker": equity_signal.get("ticker"),
            "skeptic_score": result["skeptic_score"],
            "confidence": result["confidence"],
            "model": MODEL_NAME,
        }))

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Skeptic returned invalid JSON: {e}")
        return {
            "skeptic_score": 50,
            "alternative_explanations": ["Error parsing skeptic response"],
            "sources_checked": ["parsing failed"],
            "confidence": "low",
        }
    except Exception as e:
        logger.error(f"Skeptic API error: {e}")
        return {
            "skeptic_score": 50,
            "alternative_explanations": ["Skeptic agent unavailable"],
            "sources_checked": ["API error"],
            "confidence": "low",
        }


if __name__ == "__main__":
    # Test with same data as Correlation Reasoner
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

    result = skeptic_review(test_odds, test_equity, 14.5)
    print(json.dumps(result, indent=2))