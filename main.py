from fastapi import FastAPI, Header, HTTPException
from google.cloud import firestore
import os, json, logging
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

from agents.supervisor.supervisor import evaluate_pair

app = FastAPI(title="NexaVigil API")
db = firestore.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT", "nexavigil"))
API_KEY = os.getenv("API_KEY", "dev-key")

logger = logging.getLogger("main")


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/timeline")
def get_timeline(start: str, end: str, entity: str = None):
    odds = list(db.collection("odds_events").where("timestamp", ">=", start).where("timestamp", "<=", end).stream())
    equity = list(db.collection("equity_signals").where("filing_date", ">=", start).where("filing_date", "<=", end).stream())
    return {
        "odds_events": [d.to_dict() | {"id": d.id} for d in odds],
        "equity_signals": [d.to_dict() | {"id": d.id} for d in equity]
    }


@app.get("/cases")
def list_cases():
    docs = db.collection("confluence_cases").stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


@app.get("/cases/{case_id}")
def get_case(case_id: str):
    doc = db.collection("confluence_cases").document(case_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"id": doc.id, **doc.to_dict()}


@app.post("/cases/{case_id}/feedback")
def post_feedback(case_id: str, payload: dict):
    from agents.case_memory.case_memory import update_case_feedback
    result = update_case_feedback(case_id, payload.get("feedback"), payload.get("officer_id", "maria"))
    return {"status": "feedback_recorded", "case": result}


@app.get("/registry")
def get_registry():
    docs = db.collection("agent_registry").stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]


@app.post("/run-cycle")
def run_cycle(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Fetch latest unprocessed odds and equity events
    # In production, this would query Pub/Sub or a queue
    # For demo, we use synthetic test data
    test_odds = {
        "fixture_id": "nfl-wk1-kc-buf-2026",
        "sport": "football",
        "league": "NFL",
        "market": "moneyline",
        "sportsbook": "kalshi",
        "pct_move": 0.1262,
        "timestamp": "2026-08-29T10:00:00Z",
        "event_metadata": "Sharp 12.6% move on NFL Week 1 Chiefs vs Bills at Kalshi",
        "source_type": "synthetic"
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
    
    # Run the full pipeline via Supervisor
    result = evaluate_pair(test_odds, test_equity)
    
    logger.info(json.dumps({
        "event": "pipeline_cycle_completed",
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }))
    
    return {
        "status": "cycle_completed",
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/byof/watchlist")
def set_watchlist(payload: dict, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    db.collection("byof_watchlists").document("default").set(payload)
    return {"status": "watchlist_updated"}