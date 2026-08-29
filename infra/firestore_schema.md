# Firestore Schema

## odds_events
fixture_id, sport, league, market, sportsbook, odds_before, odds_after, pct_move, timestamp, event_metadata, source_type

## equity_signals
ticker, filer_name, filer_type, transaction_type, amount, filing_date, disclosed_date, signal_type

## cases
case_id, odds_event_ref, equity_signal_ref, convergence_score, skeptic_score, alternative_explanations, reasoning_chain, evidence_list, confidence, recommended_action, status, officer_feedback, created_at

## agent_registry
agent_name, version, description, scopes, status

## officer_preferences
officer_id, ticker, pattern, false_positive_count, adjusted_threshold, last_updated
