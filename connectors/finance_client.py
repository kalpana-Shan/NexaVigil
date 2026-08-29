import requests

def get_form4_filings(ticker):
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=4&company={ticker}&count=10&output=atom"
    headers = {"User-Agent": "NexaVigil Hackathon Project research@example.com"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        return resp.text
    except Exception as e:
        return f"<error>{e}</error>"

def get_congress_trades():
    url = "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json"
    try:
        resp = requests.get(url, timeout=20)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}
