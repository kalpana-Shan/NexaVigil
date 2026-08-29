import requests, os

def skeptic_review(odds_event: dict, equity_signal: dict) -> dict:
    ticker = equity_signal.get("ticker", "")
    event_text = odds_event.get("event_metadata", "")
    api_key = os.getenv("NEWS_API_KEY")
    explanations = []
    if api_key:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={"q": f"{ticker} OR {event_text}", "sortBy": "publishedAt", "pageSize": 5, "apiKey": api_key},
                timeout=10
            )
            data = resp.json()
            for article in data.get("articles", []):
                explanations.append(article.get("title", ""))
        except Exception as e:
            explanations.append(f"newsapi_error: {e}")
    skeptic_score = 70 if len(explanations) >= 2 else (35 if len(explanations) == 1 else 10)
    return {
        "skeptic_score": skeptic_score,
        "alternative_explanations": explanations[:3],
        "sources_checked": ["newsapi"]
    }
