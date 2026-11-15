# Omega historical 2015–2025: verified access blocker (2026-11-15)

GitHub Actions run 43730414992 executed real authenticated Massive requests.

| Date | Grouped US stock daily bars | Historical ticker reference |
|---|---|---|
| 2015-01-05 | HTTP 403 | OK (sample page) |
| 2020-03-16 | HTTP 403 | OK (sample page) |
| 2025-12-31 | OK, 11,730 returned bars | OK (sample page) |

The workflow itself passed because its job is to **report entitlement status**, not to assert data access. Its final receipt was `HISTORICAL_ACCESS_INCOMPLETE`. Historical ticker responses used `limit=1` and do not establish complete delisted-universe coverage.

Historical data readiness audit run 43730150895 reported 0 sessions within 2015–2025 in the committed SQLite database, 0 SPY sessions, 0 VOO sessions and `BLOCKED_UNVERIFIED_DATA`.

**No valid 2015–2025 RippleEdge backtest exists yet. No claim of beating SPY, VOO, Berkshire Hathaway or professional funds is justified.**

Next required steps:
1. Confirm with Massive the precise historical grouped-daily entitlement covering Jan 2015–Dec 2025 **before purchasing or upgrading**. Do not assume a plan from marketing descriptions.
2. Verify the provider license permits automated research, historical storage and the intended use.
3. Obtain dated security-master records including delistings and corporate actions; validate data lineage and point-in-time fundamentals.
4. Import and audit the complete history into a separate, versioned historical database, not the live marketwide SQLite file.
5. Freeze rules, costs, rebalancing and benchmark definitions; run out-of-sample walk-forward tests and independent checks. Report total returns with dividend reinvestment, delisting handling and survivorship-bias controls.
6. Preserve raw receipts, run hashes, failures, and historical forecasts.

The repository contains `omega_walkforward.py`, an exploratory price-only primitive tested on synthetic inputs. It is **not** a substitute for the above full-cycle backtest.
