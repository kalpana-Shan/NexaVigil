import os
from google.cloud import firestore, pubsub_v1

db = firestore.Client()
publisher = pubsub_v1.PublisherClient()
project = os.getenv("GOOGLE_CLOUD_PROJECT")
topic_path = publisher.topic_path(project, "equity-signals")

def run_equity_pulse():
    print("Equity Pulse running...")
    tickers = ["DKNG", "FLUT", "MGM", "CZR", "PENN"]
    for ticker in tickers[:2]:
        doc = {
            "ticker": ticker,
            "filer_name": "Demo Filer",
            "filer_type": "insider",
            "transaction_type": "P",
            "amount": 50000,
            "filing_date": "2026-08-29",
            "disclosed_date": "2026-08-29",
            "signal_type": "form4",
            "source_type": "synthetic"
        }
        db.collection("equity_signals").add(doc)
        publisher.publish(topic_path, b"equity-signal", ticker=ticker)
    print("Published demo equity signals.")

if __name__ == "__main__":
    run_equity_pulse()
