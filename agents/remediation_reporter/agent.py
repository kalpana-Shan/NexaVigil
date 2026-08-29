import requests, os
from google.cloud import firestore

def generate_report(case: dict) -> str:
    lines = [
        f"# Case Report - {case['equity_signal']['ticker']}",
        f"**Convergence Score:** {case['convergence_score']}/100",
        f"**Skeptic Score:** {case['skeptic_score']}/100",
        f"**Confidence:** {case['confidence']}",
        "## Timeline",
        f"- Odds event: {case['odds_event']['timestamp']} - {case['odds_event'].get('pct_move',0)*100:.1f}% move",
        f"- Equity signal: {case['equity_signal']['filing_date']} - {case['equity_signal']['transaction_type']} ${case['equity_signal']['amount']}",
        "## Reasoning",
    ]
    for r in case.get("reasoning_chain", []):
        lines.append(f"- {r}")
    lines.append("## Alternative Explanations Checked")
    for e in case.get("alternative_explanations", []):
        lines.append(f"- {e}")
    lines.append("## IMPORTANT")
    lines.append("This report describes a TEMPORAL CORRELATION requiring human review.")
    lines.append("It does NOT confirm wrongdoing or insider trading.")
    return "\n".join(lines)

def send_to_slack(report_text: str):
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        print("No SLACK_WEBHOOK_URL set. Report would have been sent.")
        return
    requests.post(webhook, json={"text": report_text}, timeout=10)

def approve_and_send(case_id: str, officer_approved: bool):
    if officer_approved:
        db = firestore.Client()
        case = db.collection("cases").document(case_id).get().to_dict()
        report = generate_report(case)
        send_to_slack(report)
        db.collection("cases").document(case_id).update({"status": "reported"})
