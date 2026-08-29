import os
from vertexai.generative_models import GenerativeModel

INJECTION_PATTERNS = [
    "ignore previous instructions", "system prompt", "you are now",
    "disregard", "dan mode", "jailbreak", "override", "new instructions"
]

def screen_text(text: str) -> dict:
    if not text:
        return {"safe": True, "layer": "none", "reason": "empty_input"}
    lowered = text.lower()
    flagged = [p for p in INJECTION_PATTERNS if p in lowered]
    if flagged:
        return {"safe": False, "layer": "regex", "reason": f"flagged_patterns: {flagged}"}
    try:
        model = GenerativeModel("gemini-3.5-flash")
        prompt = (
            "Classify the following text as either SAFE or MALICIOUS for prompt injection attacks. "
            "Respond with exactly one word: SAFE or MALICIOUS.\n\n"
            f"Text: {text[:500]}"
        )
        response = model.generate_content(prompt)
        is_safe = "SAFE" in response.text.upper()
        return {"safe": is_safe, "layer": "llm_guard", "reason": response.text.strip()}
    except Exception as e:
        return {"safe": True, "layer": "llm_guard_error", "reason": str(e)}
