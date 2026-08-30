"""
Seed the Agent Registry in Firestore.
Run once to populate the registry.
"""
import os
from google.cloud import firestore
from dotenv import load_dotenv

load_dotenv()

db = firestore.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT", "nexavigil"))

AGENTS = [
    {
        "id": "odds_sentinel",
        "name": "Odds Sentinel",
        "description": "Polls prediction market data from OpticOdds",
        "version": "1.0.0",
        "status": "active",
        "scopes": ["odds:read", "anomalies:write"],
        "model": "N/A",
        "last_heartbeat": None,
    },
    {
        "id": "equity_pulse",
        "name": "Equity Pulse",
        "description": "Pulls SEC/congress/options data",
        "version": "1.0.0",
        "status": "active",
        "scopes": ["equity:read", "signals:write"],
        "model": "N/A",
        "last_heartbeat": None,
    },
    {
        "id": "correlation_reasoner",
        "name": "Correlation Reasoner",
        "description": "Scores candidate pairs using Gemini 2.5 Flash",
        "version": "1.0.0",
        "status": "active",
        "scopes": ["pairs:score", "reasoning:generate"],
        "model": "gemini-2.5-flash",
        "last_heartbeat": None,
    },
    {
        "id": "skeptic",
        "name": "Skeptic Agent",
        "description": "Debunks pairs by finding benign explanations",
        "version": "1.0.0",
        "status": "active",
        "scopes": ["pairs:debunk", "explanations:generate"],
        "model": "gemini-2.5-flash",
        "last_heartbeat": None,
    },
    {
        "id": "case_memory",
        "name": "Case Memory",
        "description": "Persists cases and handles officer feedback",
        "version": "1.0.0",
        "status": "active",
        "scopes": ["cases:crud", "feedback:process"],
        "model": "N/A",
        "last_heartbeat": None,
    },
    {
        "id": "remediation_reporter",
        "name": "Remediation Reporter",
        "description": "Generates reports and sends to Slack",
        "version": "1.0.0",
        "status": "active",
        "scopes": ["reports:generate", "slack:send"],
        "model": "N/A",
        "last_heartbeat": None,
    },
]

def seed():
    for agent in AGENTS:
        db.collection("agent_registry").document(agent["id"]).set(agent)
        print(f"Seeded: {agent['id']}")

if __name__ == "__main__":
    seed()