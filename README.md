# NexaVigil

Cross-market compliance surveillance agent fleet for the All Things Agentic Hackathon.

## Problem
Solo compliance officers like Maria Chen monitor 50+ data sources manually. When prediction market odds move sharply and related equities show unusual activity, she has no way to catch temporal correlations in real time.

## Solution Overview
NexaVigil is a fleet of 6 specialized agents that:
1. Ingests prediction market odds and equity signals
2. Correlates anomalies across markets
3. Debunks false positives with a Skeptic Agent
4. Surfaces only unexplained cases for human review

## Architecture
![Architecture](docs/architecture.png)

## Technologies Used
- Gemini 3.5 Flash (Vertex AI)
- Google ADK (Agent Development Kit)
- Gemma 2B (pre-filter + Skeptic Agent)
- Google Cloud: Cloud Run, Firestore, Pub/Sub, Cloud Scheduler, BigQuery
- Python 3.11, FastAPI, Streamlit

## Other Data Sources
- OpticOdds API (prediction market / sportsbook odds)
- SEC EDGAR (Form 4 insider filings)
- House Stock Watcher (congressional trades)
- NewsAPI (benign explanation lookup for Skeptic Agent)

## Findings & Learnings
*To be completed during build*

## Spin-Up Instructions (Local)
1. Clone repo
2. `python -m venv venv && source venv/bin/activate`
3. `pip install -r requirements.txt`
4. `cp .env.example .env` and fill in your keys
5. `uvicorn main:app --reload`
6. In another terminal: `streamlit run frontend/dashboard.py`

## Spin-Up Instructions (Cloud Deployment)
1. `gcloud auth login`
2. `gcloud config set project nexavigil`
3. `gcloud run deploy nexavigil-api --source . --region us-central1 --allow-unauthenticated --min-instances 0 --max-instances 3 --memory 512Mi`
4. `gcloud run deploy nexavigil-dashboard --source ./frontend --region us-central1 --allow-unauthenticated --min-instances 0`

## Security & Governance Notes
- Agent Identity: Separate IAM service accounts per agent (coarse-grained due to Firestore limitations; documented honestly)
- Agent Gateway: Single ingress with API key + rate limiting
- Model Armor: Two-layer defense (regex + Gemini Flash guardrail)
- Agent Observability: OpenTelemetry-compliant structured JSON logs

## Limitations & Honest Caveats
- Firestore IAM is coarse-grained; collection-level enforcement is at the application layer. Production would use Datastore Mode fine-grained access control.
- Model Armor is a two-layer defense suitable for hackathon demo. Production would integrate Google's Model Armor API or Guardrails AI.
- The system detects temporal correlations only. All outputs use non-accusatory language and require human review.
- Demo may use labeled synthetic cases replayed on live infrastructure for clarity.
