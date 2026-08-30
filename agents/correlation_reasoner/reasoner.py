"""
NexaVigil - Correlation Reasoner
Uses Gemini 2.5 Flash via Vertex AI (uses your GCP $150 credit).
MANDATORY: Uses Google AI model as required by hackathon.
NOTE: gemini-1.5-flash is RETIRED. gemini-3.5-flash has a known Vertex AI 404 bug.
      gemini-2.5-flash is GA, confirmed working, and fully qualifies.
"""
import os
import json
import logging
from typing import Dict
import vertexai
from vertexai.generative_models import GenerativeModel
from connectors.model_armor import screen_text

logger = logging.getLogger("correlation_reasoner")

# Init Vertex AI
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "nexavigil")
LOCATION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")

vertexai.init(project=PROJECT_ID, location=LOCATION)

# gemini-2.5-flash is GA on Vertex AI, confirmed working
# gemini-1.5-flash is RETIRED (Sept 2025)
# gemini-3.5-flash has known 404 bug on Vertex AI
MODEL_NAME = "gemini-2.5-flash"
model = GenerativeModel(MODEL_NAME)

# RAG context (injected into prompt)
RAG_CONTEXT = """
REGULATORY CONTEXT:
- CFTC and SEC prohibit insider trading across all markets including prediction markets.
- Kalshi and Polymarket updated insider trading rules in March 2026 following enforcement actions.
- Congressional STOCK Act requires disclosure of trades within 45 days.
- SEC Form 4 must be filed within 2 business days of insider transaction.

SCORING GUIDELINES:
- High convergence (80-100): Same entity, tight timing (<24h), unusual transaction size
- Medium convergence (50-79): Related entity, timing within 72h, some public explanation possible
- Low convergence (0-49): Weak connection, benign explanation likely, timing doesn't align
"""

PROMPT_TEMPLATE = """{rag_context}

You are a compliance analyst assistant. You NEVER declare guilt or confirm insider trading.
You only describe temporal correlations and assign a confidence score for further human review.

ODDS EVENT:
- Fixture: {fixture_id}
- Sport/League: {sport}/{league}
- Market: {market} at {sportsbook}
- Movement: {pct_move:.2%} implied probability shift
- Time: {timestamp}
- Context: {event_metadata}

EQUITY SIGNAL:
- Ticker: {ticker}
- Filer: {filer_name} ({filer_type})
- Transaction: {transaction_type} ${amount:,}
- Filing Date: {filing_date}
- Disclosed: {disclosed_date}
- Signal Type: {signal_type}

TIME GAP: {time_diff:.1f} hours

INSTRUCTIONS:
1. Analyze if the odds movement and equity signal could be related
2. Consider: same entities, timing proximity, transaction size, market context
3. Check for benign explanations (injuries, earnings, public news)
4. Return ONLY valid JSON with these exact fields:
{{
  "convergence_score": <integer 0-100>,
  "reasoning_chain": [<list of 3-5 short strings explaining your analysis>],
  "evidence_list": [<list of 2-4 specific evidence items>],
  "confidence": "low" | "medium" | "high",
  "recommended_action": <string, must say "requires human review" and nothing accusatory>
}}

CRITICAL: Use only "temporal correlation" language. Never say "insider trading", "guilty", "confirmed", "proven", or "definitely"."""


def score_pair(odds_event: Dict, equity_signal: Dict, time_diff_hours: float) -> Dict:
    """
    Score a candidate pair using Gemini via Vertex AI.
    Returns structured JSON with convergence score and reasoning.
    """
    # Screen inputs with Model Armor
    combined_text = str(odds_event.get("event_metadata", "")) + str(equity_signal.get("ticker", ""))
    armor_result = screen_text(combined_text)
    if not armor_result["safe"]:
        logger.warning(f"Model Armor blocked input: {armor_result['reason']}")
        return {
            "convergence_score": 0,
            "reasoning_chain": ["Input blocked by security filter"],
            "evidence_list": [],
            "confidence": "low",
            "recommended_action": "requires human review - security flag"
        }
    
    # Build prompt
    prompt = PROMPT_TEMPLATE.format(
        rag_context=RAG_CONTEXT,
        fixture_id=odds_event.get("fixture_id", ""),
        sport=odds_event.get("sport", ""),
        league=odds_event.get("league", ""),
        market=odds_event.get("market", ""),
        sportsbook=odds_event.get("sportsbook", ""),
        pct_move=odds_event.get("pct_move", 0),
        timestamp=odds_event.get("timestamp", ""),
        event_metadata=odds_event.get("event_metadata", ""),
        ticker=equity_signal.get("ticker", ""),
        filer_name=equity_signal.get("filer_name", ""),
        filer_type=equity_signal.get("filer_type", ""),
        transaction_type=equity_signal.get("transaction_type", ""),
        amount=equity_signal.get("amount", 0),
        filing_date=equity_signal.get("filing_date", ""),
        disclosed_date=equity_signal.get("disclosed_date", ""),
        signal_type=equity_signal.get("signal_type", ""),
        time_diff=time_diff_hours
    )
    
    # Call Gemini via Vertex AI
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Strip markdown code fences
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        result = json.loads(text.strip())
        
        # Validate non-accusatory language
        banned_words = ["insider trading", "guilty", "confirmed", "proven", "definitely"]
        full_text = " ".join(result.get("reasoning_chain", [])) + " " + result.get("recommended_action", "")
        if any(w in full_text.lower() for w in banned_words):
            logger.warning("Banned language detected in Gemini output, sanitizing")
            result["reasoning_chain"] = [r.replace("insider trading", "unusual activity") for r in result["reasoning_chain"]]
            result["recommended_action"] = "requires human review"
        
        logger.info(json.dumps({
            "event": "correlation_scored",
            "fixture_id": odds_event.get("fixture_id"),
            "ticker": equity_signal.get("ticker"),
            "convergence_score": result.get("convergence_score"),
            "confidence": result.get("confidence"),
            "model": MODEL_NAME
        }))
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned invalid JSON: {e}")
        return {
            "convergence_score": 0,
            "reasoning_chain": ["Error parsing model response"],
            "evidence_list": [],
            "confidence": "low",
            "recommended_action": "requires human review - parsing error"
        }
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return {
            "convergence_score": 0,
            "reasoning_chain": ["Model API error"],
            "evidence_list": [],
            "confidence": "low",
            "recommended_action": "requires human review - API error"
        }


if __name__ == "__main__":
    # Test
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
    
    result = score_pair(test_odds, test_equity, 14.5)
    print(json.dumps(result, indent=2))