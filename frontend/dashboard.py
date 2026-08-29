import streamlit as st
import requests, os

API_URL = os.getenv("API_URL", "http://localhost:8080")
API_KEY = os.getenv("API_KEY", "dev-key")

st.set_page_config(page_title="NexaVigil", layout="wide")
st.title("NexaVigil - Cross-Market Compliance Dashboard")

tab1, tab2, tab3 = st.tabs(["Live Feed", "Cases", "Agent Registry"])

with tab1:
    st.subheader("Recent Odds Anomalies & Equity Signals")
    try:
        data = requests.get(f"{API_URL}/timeline", params={"start":"2026-08-01","end":"2026-09-01"}, headers={"X-API-Key": API_KEY}, timeout=10).json()
        st.json(data)
    except Exception as e:
        st.error(f"Error fetching timeline: {e}")

with tab2:
    st.subheader("Open Cases")
    try:
        cases = requests.get(f"{API_URL}/cases", headers={"X-API-Key": API_KEY}, timeout=10).json()
        for case in cases:
            with st.expander(f"{case['equity_signal']['ticker']} - Score: {case['convergence_score']}"):
                st.write("Reasoning:", case.get("reasoning_chain", []))
                st.write("Skeptic Score:", case.get("skeptic_score"))
                st.write("Alternative Explanations:", case.get("alternative_explanations", []))
                feedback = st.text_input(f"Officer note for {case['id']}", key=f"note_{case['id']}")
                if st.button(f"Submit feedback {case['id']}", key=f"btn_{case['id']}"):
                    requests.post(f"{API_URL}/cases/{case['id']}/feedback", json={"message": feedback}, headers={"X-API-Key": API_KEY})
                    st.success("Feedback recorded")
    except Exception as e:
        st.error(f"Error fetching cases: {e}")

with tab3:
    st.subheader("Agent Registry")
    try:
        registry = requests.get(f"{API_URL}/registry", headers={"X-API-Key": API_KEY}, timeout=10).json()
        st.table(registry)
    except Exception as e:
        st.error(f"Error fetching registry: {e}")
