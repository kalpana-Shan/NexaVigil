"""
NexaVigil - Odds Sentinel Agent
Polls prediction market odds and flags anomalies.
For hackathon: uses synthetic data generator when OpticOdds API is unavailable.
"""
import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from google.cloud import firestore, pubsub_v1
from connectors.opticodds_client import get_active_fixtures, get_fixture_odds

# Setup structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("odds_sentinel")

# Firestore + Pub/Sub clients
db = firestore.Client()
publisher = pubsub_v1.PublisherClient()
project = os.getenv("GOOGLE_CLOUD_PROJECT", "nexavigil")
topic_path = publisher.topic_path(project, "odds-anomalies")

# Config
THRESHOLD_PCT_MOVE = 0.08  # 8% implied probability shift
ROLLING_WINDOWS = [5, 30, 120]  # minutes
DEMO_LEAGUES = [("basketball", "NBA"), ("football", "NFL")]


def compute_implied_prob(odds: float) -> float:
    """Convert decimal odds to implied probability."""
    if odds <= 0:
        return 0.0
    return 1.0 / odds


def compute_pct_move(old_prob: float, new_prob: float) -> float:
    """Compute percentage change in implied probability."""
    if old_prob == 0:
        return 0.0
    return (new_prob - old_prob) / old_prob


def get_last_odds_snapshot(fixture_id: str, sportsbook: str, market: str) -> Optional[Dict]:
    """Retrieve last stored odds for a fixture from Firestore."""
    try:
        docs = (
            db.collection("odds_events")
            .where("fixture_id", "==", fixture_id)
            .where("sportsbook", "==", sportsbook)
            .where("market", "==", market)
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        for d in docs:
            return d.to_dict()
        return None
    except Exception as e:
        logger.error(json.dumps({
            "event": "firestore_read_error",
            "fixture_id": fixture_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }))
        return None


def detect_steam_move(fixture_id: str, sport: str, league: str, market: str, 
                      sportsbook: str, current_odds: float) -> Optional[Dict]:
    """
    Detect if odds movement exceeds threshold.
    Returns OddsEvent dict if anomaly detected, None otherwise.
    """
    last = get_last_odds_snapshot(fixture_id, sportsbook, market)
    
    old_prob = compute_implied_prob(last["odds_after"]) if last else compute_implied_prob(current_odds)
    new_prob = compute_implied_prob(current_odds)
    pct_move = compute_pct_move(old_prob, new_prob)
    
    # Check if movement exceeds threshold
    if abs(pct_move) >= THRESHOLD_PCT_MOVE:
        event = {
            "fixture_id": fixture_id,
            "sport": sport,
            "league": league,
            "market": market,
            "sportsbook": sportsbook,
            "odds_before": last["odds_after"] if last else current_odds,
            "odds_after": current_odds,
            "pct_move": round(pct_move, 4),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_metadata": f"{sportsbook} {market} moved {pct_move*100:.1f}% on {fixture_id}",
            "source_type": "live" if os.getenv("OPTICODDS_API_KEY") else "synthetic"
        }
        return event
    return None


def generate_synthetic_odds() -> List[Dict]:
    """
    Generate realistic synthetic odds data for demo.
    Used when OpticOdds API key is not available.
    """
    import random
    
    fixtures = [
        {"fixture_id": "nfl-wk1-kc-buf-2026", "sport": "football", "league": "NFL", 
         "market": "moneyline", "sportsbook": "kalshi", "base_odds": 1.85},
        {"fixture_id": "nfl-wk1-dal-phi-2026", "sport": "football", "league": "NFL", 
         "market": "spread", "sportsbook": "polymarket", "base_odds": 1.95},
        {"fixture_id": "nba-finals-g1-2026", "sport": "basketball", "league": "NBA", 
         "market": "moneyline", "sportsbook": "kalshi", "base_odds": 1.75},
    ]
    
    events = []
    for fixture in fixtures:
        # Simulate sharp move (10-15%)
        base = fixture.pop("base_odds")
        move = random.uniform(0.10, 0.15) * random.choice([-1, 1])
        new_odds = round(base * (1 - move), 2)
        
        event = {
            **fixture,
            "odds_before": base,
            "odds_after": new_odds,
            "pct_move": round(move, 4),
            "timestamp": (datetime.utcnow() - timedelta(minutes=random.randint(5, 120))).isoformat() + "Z",
            "event_metadata": f"Sharp {abs(move)*100:.1f}% move on {fixture['fixture_id']} at {fixture['sportsbook']}",
            "source_type": "synthetic"
        }
        events.append(event)
    
    logger.info(json.dumps({
        "event": "synthetic_odds_generated",
        "count": len(events),
        "timestamp": datetime.utcnow().isoformat()
    }))
    return events


def publish_odds_event(event: Dict) -> str:
    """Write odds event to Firestore and publish to Pub/Sub."""
    try:
        # Write to Firestore
        doc_ref = db.collection("odds_events").add(event)
        doc_id = doc_ref[1].id
        
        # Publish to Pub/Sub
        message = json.dumps(event).encode("utf-8")
        future = publisher.publish(
            topic_path, 
            message,
            fixture_id=event["fixture_id"],
            source_type=event["source_type"]
        )
        message_id = future.result()
        
        logger.info(json.dumps({
            "event": "odds_anomaly_published",
            "fixture_id": event["fixture_id"],
            "doc_id": doc_id,
            "message_id": message_id,
            "pct_move": event["pct_move"],
            "timestamp": datetime.utcnow().isoformat()
        }))
        return doc_id
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "publish_error",
            "fixture_id": event.get("fixture_id"),
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }))
        raise


def run_odds_sentinel():
    """Main entry point for Odds Sentinel agent."""
    logger.info(json.dumps({
        "event": "odds_sentinel_start",
        "threshold": THRESHOLD_PCT_MOVE,
        "timestamp": datetime.utcnow().isoformat()
    }))
    
    api_key = os.getenv("OPTICODDS_API_KEY")
    
    if api_key:
        # Real OpticOdds polling (production path)
        logger.info("Using OpticOdds API")
        for sport, league in DEMO_LEAGUES:
            fixtures = get_active_fixtures(sport, league)
            if "error" in fixtures:
                logger.warning(f"OpticOdds error: {fixtures['error']}")
                continue
            for fixture in fixtures.get("data", []):
                odds_data = get_fixture_odds(fixture["id"])
                # ... parse and detect moves ...
    else:
        # Synthetic data path (hackathon demo)
        logger.info("Using synthetic odds data")
        events = generate_synthetic_odds()
        for event in events:
            publish_odds_event(event)
    
    logger.info(json.dumps({
        "event": "odds_sentinel_complete",
        "timestamp": datetime.utcnow().isoformat()
    }))


if __name__ == "__main__":
    run_odds_sentinel()