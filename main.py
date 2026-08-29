from fastapi import FastAPI, Header, HTTPException
from google.cloud import firestore
import os, json, logging
from datetime import datetime

app = FastAPI(title="NexaVigil API")
db = firestore.Client()
API_KEY = os.getenv("API_KEY", "dev-key")

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

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
    docs = db.collection("cases").stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]

@app.post("/cases/{case_id}/feedback")
def post_feedback(case_id: str, payload: dict):
    db.collection("cases").document(case_id).set({
        "officer_feedback": payload,
        "updated_at": datetime.utcnow().isoformat()
    }, merge=True)
    return {"status": "feedback_recorded"}

@app.get("/registry")
def get_registry():
    docs = db.collection("agent_registry").stream()
    return [{"id": d.id, **d.to_dict()} for d in docs]

@app.post("/run-cycle")
def run_cycle(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {"status": "cycle_triggered", "timestamp": datetime.utcnow().isoformat()}

@app.post("/byof/watchlist")
def set_watchlist(payload: dict, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    db.collection("byof_watchlists").document("default").set(payload)
    return {"status": "watchlist_updated"}
