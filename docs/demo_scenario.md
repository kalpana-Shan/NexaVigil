# Demo Scenario

## Synthetic Replay on Live Infrastructure

**Date:** August 20, 2026
**Event:** Kalshi prediction market odds on NFL Week 1 moved sharply (-12% implied probability shift in 20 minutes).
**Equity Signal:** Within 48 hours, unusual call options volume spiked on DKNG.

**Pipeline:**
1. Odds Sentinel detects line movement, publishes anomaly
2. Equity Pulse detects options flow, publishes signal
3. Supervisor pairs them (entity keyword match)
4. Correlation Reasoner scores 78/100 - "requires human review"
5. Skeptic Agent checks NewsAPI - no benign explanation found. Skeptic score: 15/100.
6. Case Memory creates case (convergence >= 60 AND skeptic < 30).
7. Officer Maria reviews in dashboard, approves.
8. Remediation Reporter posts Markdown report to Slack.

**Transparency:** This is a labeled synthetic case injected into live Firestore/Pub/Sub infrastructure for demo clarity. All pipeline execution is real.
