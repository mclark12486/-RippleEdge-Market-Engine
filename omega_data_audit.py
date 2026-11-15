"""Omega 2015-2025 full-cycle data readiness gate.

This is an evidence audit, NOT a historical strategy performance result.
Never silently substitute a current ticker census for a historical universe.
"""
import datetime as dt
import json
import sqlite3
from pathlib import Path

START="2015-01-01"
END="2025-12-31"
REQUIRED=("SPY","VOO")

def audit(db,manifest=None):
 manifest=manifest or {}
 # Historical total-return / delisting / point-in-time provenance requires
 # explicit independently documented evidence, not inference from price bars.
 result={"period":[START,END],"status":"BLOCKED_UNVERIFIED_DATA",
  "historical_sessions":0,"benchmark_sessions":{},
  "missing_benchmark_sessions":0,"security_universe_verified":False,
  "point_in_time_fundamentals_verified":False,
  "corporate_actions_verified":False,"delisting_returns_verified":False,
  "price_total_returns_verified":False,"strategy_results":None,
  "limitations":[]}
 tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 if "daily_bars" not in tables:
  result["limitations"].append("daily_bars table missing");return result
 dates=[r[0] for r in db.execute("SELECT DISTINCT session FROM daily_bars WHERE session BETWEEN ? AND ? ORDER BY session",(START,END))]
 result["historical_sessions"]=len(dates)
 for sym in REQUIRED:
  result["benchmark_sessions"][sym]=db.execute("SELECT COUNT(DISTINCT session) FROM daily_bars WHERE symbol=? AND session BETWEEN ? AND ?",(sym,START,END)).fetchone()[0]
 result["missing_benchmark_sessions"]=sum(1 for d in dates if any(
  not db.execute("SELECT 1 FROM daily_bars WHERE symbol=? AND session=? LIMIT 1",(sym,d)).fetchone() for sym in REQUIRED))
 for k in ("security_universe_verified","point_in_time_fundamentals_verified",
           "corporate_actions_verified","delisting_returns_verified","price_total_returns_verified"):
  # Do not accept a boolean claim without source, SHA256, and an audit record.
  evidence=manifest.get(k)
  result[k]=bool(isinstance(evidence,dict) and evidence.get("verified") is True
                 and evidence.get("source") and evidence.get("sha256")
                 and evidence.get("audit_receipt"))
 if not dates or dates[0]>"2015-01-05" or dates[-1]<"2025-12-31":
  result["limitations"].append("Full 2015-2025 daily history not present")
 if result["missing_benchmark_sessions"] or any(result["benchmark_sessions"][s]!=len(dates) for s in REQUIRED):
  result["limitations"].append("SPY/VOO daily coverage incomplete")
 for k in ("security_universe_verified","point_in_time_fundamentals_verified",
           "corporate_actions_verified","delisting_returns_verified","price_total_returns_verified"):
  if not result[k]:result["limitations"].append(k+" missing independently verified evidence")
 # Presence of first and last sessions does not prove all expected trading dates.
 result["limitations"].append("Exchange-calendar completeness and source authenticity require independent validation")
 return result

def main():
 dbpath=Path("state/marketwide.sqlite")
 if not dbpath.exists():raise SystemExit("BLOCKED: marketwide SQLite missing")
 manifestpath=Path("state/omega_data_manifest.json")
 manifest=json.loads(manifestpath.read_text()) if manifestpath.exists() else {}
 with sqlite3.connect(dbpath) as db:report=audit(db,manifest)
 out=Path("state/omega_2015_2025_readiness.json")
 out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
 print(json.dumps(report,indent=2,sort_keys=True))
if __name__=="__main__":main()
