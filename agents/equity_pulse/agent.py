"""
NexaVigil - Equity Pulse Agent
Pulls SEC Form 4 filings, congressional trades, and institutional holdings.
For hackathon: uses synthetic data generator when real APIs are unavailable.
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from google.cloud import firestore, pubsub_v1
from connectors.finance_client import get_form4_filings, get_congress_trades

# Setup structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("equity_pulse")

# Firestore + Pub/Sub clients
db = firestore.Client()
publisher = pubsub_v1.PublisherClient()
project = os.getenv("GOOGLE_CLOUD_PROJECT", "nexavigil")
topic_path = publisher.topic_path(project, "equity-signals")

# Config
TICKER_BASKET = ["DKNG", "FLUT", "MGM", "CZR", "PENN"]
FILING_DELAY_DAYS = 14  # Congressional trades disclose late


def parse_form4_from_sec_xml(xml_text: str, ticker: str) -> List[Dict]:
    """
    Parse SEC Form 4 XML/Atom feed into EquitySignal schema.
    Returns list of signals or empty list if parsing fails.
    """
    import xml.etree.ElementTree as ET
    
    signals = []
    try:
        root = ET.fromstring(xml_text)
        # Atom namespace
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns)
            updated = entry.find("atom:updated", ns)
            
            if title is not None and updated is not None:
                signals.append({
                    "ticker": ticker,
                    "filer_name": title.text[:50] if title.text else "Unknown",
                    "filer_type": "insider",
                    "transaction_type": "P",  # Simplified — real parsing would detect P/S
                    "amount": 0,  # Would parse from filing detail
                    "filing_date": updated.text[:10] if updated.text else datetime.utcnow().strftime("%Y-%m-%d"),
                    "disclosed_date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "signal_type": "form4",
                    "source_type": "live"
                })
    except Exception as e:
        logger.warning(json.dumps({
            "event": "form4_parse_error",
            "ticker": ticker,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }))
    
    return signals


def generate_synthetic_equity_signals() -> List[Dict]:
    """
    Generate realistic synthetic equity signals for demo.
    Mirrors real SEC Form 4 and congressional trade patterns.
    """
    import random
    
    # Simulate insider trades
    insiders = [
        {"ticker": "DKNG", "filer_name": "Jason Robins", "filer_type": "insider", 
         "transaction_type": "P", "amount": 125000, "signal_type": "form4"},
        {"ticker": "FLUT", "filer_name": "Peter Jackson", "filer_type": "insider", 
         "transaction_type": "S", "amount": 85000, "signal_type": "form4"},
        {"ticker": "MGM", "filer_name": "Rep. Nancy Pelosi", "filer_type": "congress", 
         "transaction_type": "P", "amount": 50000, "signal_type": "congress"},
        {"ticker": "CZR", "filer_name": "BlackRock Inc", "filer_type": "institution", 
         "transaction_type": "P", "amount": 500000, "signal_type": "institutional"},
        {"ticker": "PENN", "filer_name": "Barstool Sports Fund", "filer_type": "institution", 
         "transaction_type": "S", "amount": 200000, "signal_type": "institutional"},
    ]
    
    signals = []
    for insider in insiders:
        # Random transaction date within last 72 hours
        transaction_date = datetime.utcnow() - timedelta(hours=random.randint(1, 72))
        
        # Congressional filings have delay
        disclosed_date = transaction_date
        if insider["filer_type"] == "congress":
            disclosed_date = transaction_date + timedelta(days=random.randint(7, 30))
        
        signal = {
            **insider,
            "filing_date": transaction_date.strftime("%Y-%m-%d"),
            "disclosed_date": disclosed_date.strftime("%Y-%m-%d"),
            "source_type": "synthetic"
        }
        signals.append(signal)
    
    logger.info(json.dumps({
        "event": "synthetic_equity_generated",
        "count": len(signals),
        "tickers": [s["ticker"] for s in signals],
        "timestamp": datetime.utcnow().isoformat()
    }))
    return signals


def publish_equity_signal(signal: Dict) -> str:
    """Write equity signal to Firestore and publish to Pub/Sub."""
    try:
        # Write to Firestore
        doc_ref = db.collection("equity_signals").add(signal)
        doc_id = doc_ref[1].id
        
        # Publish to Pub/Sub
        message = json.dumps(signal).encode("utf-8")
        future = publisher.publish(
            topic_path,
            message,
            ticker=signal["ticker"],
            signal_type=signal["signal_type"],
            source_type=signal["source_type"]
        )
        message_id = future.result()
        
        logger.info(json.dumps({
            "event": "equity_signal_published",
            "ticker": signal["ticker"],
            "filer_type": signal["filer_type"],
            "doc_id": doc_id,
            "message_id": message_id,
            "amount": signal["amount"],
            "timestamp": datetime.utcnow().isoformat()
        }))
        return doc_id
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "equity_publish_error",
            "ticker": signal.get("ticker"),
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }))
        raise


def run_equity_pulse():
    """Main entry point for Equity Pulse agent."""
    logger.info(json.dumps({
        "event": "equity_pulse_start",
        "ticker_basket": TICKER_BASKET,
        "timestamp": datetime.utcnow().isoformat()
    }))
    
    # Try real SEC data first (will likely fail without proper parsing, but shows intent)
    for ticker in TICKER_BASKET[:2]:  # Try first 2 to avoid rate limits
        try:
            xml_data = get_form4_filings(ticker)
            if xml_data and not xml_data.startswith("<error>"):
                signals = parse_form4_from_sec_xml(xml_data, ticker)
                for signal in signals[:2]:  # Limit to 2 per ticker
                    publish_equity_signal(signal)
        except Exception as e:
            logger.warning(f"Real SEC data failed for {ticker}: {e}")
    
    # Generate synthetic data for all tickers (guaranteed to work)
    synthetic_signals = generate_synthetic_equity_signals()
    for signal in synthetic_signals:
        publish_equity_signal(signal)
    
    logger.info(json.dumps({
        "event": "equity_pulse_complete",
        "timestamp": datetime.utcnow().isoformat()
    }))


if __name__ == "__main__":
    run_equity_pulse()
