import os, json
import vertexai
from vertexai.generative_models import GenerativeModel

vertexai.init(project=os.getenv("GOOGLE_CLOUD_PROJECT"), location="us-central1")
model = GenerativeModel("gemini-3.5-flash")

PROMPT_TEMPLATE = '''You are a compliance analyst assistant. You NEVER declare guilt or confirm insider trading.
You only describe temporal correlations and assign a confidence score for further human review.

Odds event: {odds_event}
Equity signal: {equity_signal}
Time gap (hours): {time_diff}

Return ONLY valid JSON with these exact fields:
{{
  "convergence_score": <integer 0-100>,
  "reasoning_chain": [<list of short strings>],
  "evidence_list": [<list of short strings>],
  "confidence": "low" | "medium" | "high",
  "recommended_action": <string, must say "requires human review" and nothing accusatory>
}}'''

def score_pair(odds_event, equity_signal, time_diff_hours: float):
    prompt = PROMPT_TEMPLATE.format(
        odds_event=json.dumps(odds_event),
        equity_signal=json.dumps(equity_signal),
        time_diff=time_diff_hours
    )
    response = model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())
