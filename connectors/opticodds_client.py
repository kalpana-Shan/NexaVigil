import requests, os

BASE_URL = "https://api.opticodds.com/api/v3"
API_KEY = os.getenv("OPTICODDS_API_KEY")

def get_active_fixtures(sport, league):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {"sport": sport, "league": league}
    try:
        resp = requests.get(f"{BASE_URL}/fixtures/active", headers=headers, params=params, timeout=10)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def get_fixture_odds(fixture_id):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        resp = requests.get(f"{BASE_URL}/fixtures/odds", headers=headers, params={"fixture_id": fixture_id}, timeout=10)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}
