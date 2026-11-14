# RippleEdge Market Engine

An evidence-driven, scheduled market census and SEC filing intake system. **No trades are placed and no forecasts are changed.** This repository does not replace the authoritative RippleEdge v4.2 ledger.

## Two independent workflows

**Market-wide census and SEC index** (`.github/workflows/marketwide.yml`) runs hourly and can be started manually from GitHub Actions. It downloads the Nasdaq Trader Nasdaq-listed and other-exchange directories, records symbol, listing venue, and ETF flags, and checks SEC daily master indexes. It saves a SQLite research database and an immutable timestamped receipt in `state/`.

**Legacy SEC submissions intake** (`.github/workflows/hourly.yml`) separately checks SEC company CIK submissions and uploads a large SQLite artifact. SEC company identifiers are **not** a complete listed stock/ETF census.

## Run and verify

1. Set the GitHub Actions secret `SEC_USER_AGENT` to a truthful identifying contact string.
2. Go to **Actions → RippleEdge market-wide census and SEC index → Run workflow → main → Run workflow**.
3. Inspect the newest `state/marketwide_receipt_*.json`. Check `feeds`, `census_rows`, `sec_indexes`, and `full_market_hourly_coverage`.
4. A green workflow confirms execution, **not** that every listed security received a filing, price, or valuation audit.

## Verified baseline (November 14, 2026)

The first market-wide workflow succeeded and recorded 13,248 unique listed symbols: 5,596 Nasdaq-listed and 7,652 other-exchange-listed, including 5,787 ETF-flagged securities. SEC daily index ingestion recorded **zero filings** because its index requests failed or were rejected by the parser. A parser correction was subsequently committed and requires a new execution to verify.

## Engineering constraints and remaining work

- **SEC filing coverage:** SEC daily indexes are not live event streams. Access can fail or be delayed. The index parser was corrected; success must be confirmed in the next run.
- **Market prices and volume:** No licensed, exchange-wide intraday bulk feed is connected. A symbol census is not price coverage.
- **Other catalysts:** FDA, procurement, permits, patents, hiring, and issuer releases require additional source-specific ingestion and verification.
- **ETF valuation:** Listing flags do not supply holdings, NAV, flows, or tracking data.
- **Forensic valuation:** SEC filings alone do not create reconciled bear/base/bull models or reliable trading entries.
- **Persistence:** The compact marketwide SQLite database is committed between runs, but GitHub is not a production database; GitHub Actions schedules may be delayed. The legacy scanner stores its larger SQLite as a workflow artifact and does not yet restore that artifact automatically.
- **Data integrity:** Previous receipts and forecasts must remain immutable; do not infer historical market coverage or learning success from a green workflow.

**Status:** exchange-directory census operational; complete hourly market-wide filing, price, event, and valuation coverage **not yet verified**. All unsupported coverage must be reported as blocked rather than fabricated.
