from google.cloud import firestore

db = firestore.Client()

agents = [
    {"agent_name": "odds_sentinel", "version": "1.0.0", "description": "Ingests prediction market odds and flags anomalies", "scopes": ["odds_events:read", "odds_events:write"], "status": "active"},
    {"agent_name": "equity_pulse", "version": "1.0.0", "description": "Ingests SEC and congressional trade filings", "scopes": ["equity_signals:read", "equity_signals:write"], "status": "active"},
    {"agent_name": "correlation_reasoner", "version": "1.0.0", "description": "Scores candidate pairs using Gemini 3.5 Flash", "scopes": ["cases:write"], "status": "active"},
    {"agent_name": "skeptic", "version": "1.0.0", "description": "Debunks correlations by finding benign explanations", "scopes": ["cases:read"], "status": "active"},
    {"agent_name": "case_memory", "version": "1.0.0", "description": "Manages persistent cases and officer feedback", "scopes": ["cases:read", "cases:write", "officer_preferences:write"], "status": "active"},
    {"agent_name": "remediation_reporter", "version": "1.0.0", "description": "Generates reports and sends to Slack", "scopes": ["cases:read"], "status": "active"},
    {"agent_name": "supervisor", "version": "1.0.0", "description": "Orchestrates the full pipeline", "scopes": ["all:read"], "status": "active"},
]

for a in agents:
    db.collection("agent_registry").document(a["agent_name"]).set(a)

print("Agent registry seeded.")
