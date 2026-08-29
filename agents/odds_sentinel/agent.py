import os
from google.cloud import firestore, pubsub_v1

db = firestore.Client()
publisher = pubsub_v1.PublisherClient()
project = os.getenv("GOOGLE_CLOUD_PROJECT")
topic_path = publisher.topic_path(project, "odds-anomalies")

def run_odds_sentinel():
    print("Odds Sentinel running...")
    doc = {
        "fixture_id": "demo-001",
        "sport": "basketball",
        "league": "NBA",
        "market": "moneyline",
        "sportsbook": "demo_book",
        "odds_before": 1.90,
        "odds_after": 1.70,
        "pct_move": 0.105,
        "timestamp": "2026-08-29T12:00:00Z",
        "event_metadata": "sharp move on Lakers game",
        "source_type": "synthetic"
    }
    db.collection("odds_events").add(doc)
    publisher.publish(topic_path, b"odds-anomaly", fixture_id="demo-001")
    print("Published demo odds event.")

if __name__ == "__main__":
    run_odds_sentinel()
