# RippleEdge Market Engine — SEC Intake Prototype

Runs hourly through GitHub Actions when enabled and configured. It enumerates SEC company CIK/ticker mappings and rotates SEC submissions checks by least recently checked CIK. Each completed run commits a SQLite snapshot and JSON coverage receipt. The original RippleEdge v4.2 forecasts and ledgers are not imported or modified.

## Setup
1. Add repository Actions secret `SEC_USER_AGENT` with a truthful contact string such as `RippleEdge Research contact@example.com`. Never commit personal credentials.
2. Enable GitHub Actions if prompted, then run **Actions → RippleEdge hourly SEC intake → Run workflow**.
3. Inspect `state/receipt_*.json` and the workflow logs. A green workflow alone is not proof of full coverage.

## Limitations
SEC company_tickers.json is **not** an exchange-complete stock/ETF master. Per-CIK submissions requests can exceed the hourly job's 55-minute timeout, so many CIKs may be unchecked. The SEC also rate-limits access; honor its fair-access policy. This prototype does not supply live prices, ETF holdings, DCF valuations, prospective forecasts, or true full-market hourly coverage. GitHub repository storage is not ideal for growing SQLite histories; migrate to a durable database and bulk feeds before scaling. No trading occurs.
