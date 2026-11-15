"""Omega portfolio monitor and paper-only exit simulation.

Never routes broker orders. Requires a fresh broker-sourced snapshot for
portfolio-specific decisions. A paper exit does not imply a real fill.
"""
import datetime as dt,json,math
from pathlib import Path
from omega_drawdown_triage import triage
def monitor(snapshot,now=None):
 now=now or dt.datetime.now(dt.timezone.utc)
 required=("asof","source","equity","previous_close_equity","peak_equity",
           "market_day_return","positions","estimated_gap_risk")
 if any(k not in snapshot for k in required):
  return {"status":"BLOCKED_MISSING_PORTFOLIO_DATA","paper_orders":[]}
 try:
  asof=dt.datetime.fromisoformat(snapshot["asof"].replace("Z","+00:00"))
  if asof.tzinfo is None:raise ValueError("timezone")
  age=(now-asof).total_seconds()/60
  eq=float(snapshot["equity"]);prev=float(snapshot["previous_close_equity"])
  peak=float(snapshot["peak_equity"])
  if not all(math.isfinite(x) and x>0 for x in (eq,prev,peak)) or not 0<=age<=15:
   raise ValueError("stale or invalid equity")
  if snapshot["source"] not in ("broker_verified","manual_confirmed"):
   raise ValueError("unverified source")
  positions=snapshot["positions"]
  if not isinstance(positions,list):raise ValueError("positions")
  for item in positions:
   if not all(k in item for k in ("symbol","market_value","thesis_broken")):raise ValueError("position fields")
   if float(item["market_value"])<0 or not math.isfinite(float(item["market_value"])):raise ValueError("position value")
 except (TypeError,ValueError,KeyError):
  return {"status":"BLOCKED_STALE_OR_UNVERIFIED","paper_orders":[]}
 day=eq/prev-1;dd=max(0,1-eq/peak)
 exposure=sum(float(x["market_value"]) for x in positions)/eq
 risk=triage({"portfolio_day_return":day,"portfolio_peak_drawdown":dd,
  "market_day_return":snapshot["market_day_return"],
  "thesis_broken":any(x["thesis_broken"] is True for x in positions),
  "price_data_fresh":True,"exposure_fraction":min(exposure,1),
  "estimated_gap_risk":snapshot["estimated_gap_risk"]})
 paper=[]
 if risk["action"] in ("EMERGENCY_REVIEW","DE_RISK_REVIEW","THESIS_EXIT_REVIEW"):
  for item in positions:
   if item["thesis_broken"] is True or risk["action"]=="EMERGENCY_REVIEW":
    paper.append({"symbol":item["symbol"],"action":"REVIEW_SELL",
                  "notional_usd":round(float(item["market_value"]),2),
                  "execution":"NONE_PAPER_ONLY"})
 return {"status":"SHADOW_MONITOR_ONLY","source":snapshot["source"],
  "age_minutes":round(age,2),"portfolio_day_return":round(day,6),
  "portfolio_drawdown":round(dd,6),"risk":risk,"paper_orders":paper,
  "warning":"No broker connection, automatic trading, guaranteed stop or verified execution."}
def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument("--snapshot",required=True)
 ap.add_argument("--receipt",default="state/omega_portfolio_monitor_receipt.json")
 a=ap.parse_args()
 r=monitor(json.loads(Path(a.snapshot).read_text()))
 Path(a.receipt).parent.mkdir(parents=True,exist_ok=True)
 Path(a.receipt).write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
 print(json.dumps(r,indent=2,sort_keys=True))
if __name__=="__main__":main()
