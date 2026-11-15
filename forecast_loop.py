"""Shadow-only market-data forecast loop: freeze prospectively and score after horizon.
Signals are price-pattern hypotheses, NOT verified catalysts or investment advice.
"""
import datetime as dt
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from forecast_ledger import freeze, score, summary, initialize

UTC=dt.timezone.utc
PROVIDER="Massive/Polygon"
def utcnow():return dt.datetime.now(UTC)
def iso(t):return t.isoformat().replace("+00:00","Z")

def run(db, current, max_candidates=15):
 initialize(db)
 latest=db.execute("SELECT session,status,matched FROM price_runs ORDER BY checked_at DESC LIMIT 1").fetchone()
 report={"checked_at":iso(current),"status":"BLOCKED","new_forecasts":0,"outcomes_scored":0,
         "pending":0,"blocked":0,"latest_price_run":latest[0] if latest else None}
 if not latest or latest[1]=="PRICE_FEED_BLOCKED" or latest[2]<1:
  report["reason"]="No usable licensed grouped-bar feed in latest run";return report
 session=latest[0]
 if not session:
  report["reason"]="No provider session";return report
 try:age=(current.date()-dt.date.fromisoformat(session)).days
 except ValueError:
  report["reason"]="Invalid session date";return report
 if age<0 or age>5:
  report["reason"]="Market data stale or future dated";return report
 benchmark=db.execute("SELECT close FROM daily_bars WHERE symbol='SPY' AND session=? AND provider=?",(session,PROVIDER)).fetchone()
 voo_base=db.execute("SELECT close FROM daily_bars WHERE symbol='VOO' AND session=? AND provider=?",(session,PROVIDER)).fetchone()
 if not benchmark or benchmark[0]<=0 or not voo_base or voo_base[0]<=0:
  report["reason"]="SPY or VOO benchmark missing from current provider session";return report
 # Freeze only signals generated for the latest verified session. Never backdate
 # the freeze timestamp or infer a prediction from a historical price move.
 candidates=db.execute("""SELECT b.symbol,b.signal,b.metric,d.close
 FROM breadth_signals b JOIN daily_bars d ON d.symbol=b.symbol AND d.session=b.session AND d.provider=?
 WHERE b.session=? AND b.signal='RELATIVE_VOLUME'
 ORDER BY b.metric DESC,b.symbol LIMIT ?""",(PROVIDER,session,max_candidates)).fetchall()
 for symbol,signal,metric,entry in candidates:
  if not entry or entry<=0 or symbol=="SPY":continue
  exists=db.execute("SELECT 1 FROM shadow_forecasts WHERE symbol=? AND json_extract(record_json,'$.signal_session')=? AND json_extract(record_json,'$.signal_type')=?",(symbol,session,signal)).fetchone()
  if exists:continue
  frozen_at=iso(current)
  record={"symbol":symbol,"frozen_at":frozen_at,"evidence_cutoff":frozen_at,
   "direction":"LONG","entry_price":entry,"entry_band":[entry,entry],
   "invalidation":"Shadow research only; not an executable stop",
   "horizon":"5 trading sessions","horizon_sessions":5,"benchmark":"SPY","benchmark_pair":"SPY_VOO",
   "costs":"20 bps illustrative round-trip","cost_bps":20,
   "source_receipts":[f"Massive/Polygon daily_bars:{symbol}:{session}",f"breadth_signals:{symbol}:{session}:{signal}"],
   "signal_session":session,"signal_type":signal,"signal_metric":metric,
   "entry_type":"INDICATIVE_PRIOR_CLOSE_NOT_EXECUTED","hypothesis":"Abnormal volume may precede 5-session relative strength; prospective test only",
   "catalyst_verified":False}
  result=freeze(db,record)
  if result["status"]=="FROZEN":report["new_forecasts"]+=1
  else:report["blocked"]+=1
 # Score each frozen forecast using five later observed sessions and SPY at
 # the same source-date baseline. No outcome if SPY or issuer bars are missing.
 rows=db.execute("SELECT forecast_id,record_json FROM shadow_forecasts").fetchall()
 for fid,raw in rows:
  f=json.loads(raw)
  if db.execute("SELECT 1 FROM shadow_outcomes WHERE forecast_id=?",(fid,)).fetchone():continue
  start=f["frozen_at"][:10]
  base=db.execute("SELECT close FROM daily_bars WHERE symbol='SPY' AND session=? AND provider=?",(f.get("signal_session"),PROVIDER)).fetchone()
  voo_start=db.execute("SELECT close FROM daily_bars WHERE symbol='VOO' AND session=? AND provider=?",(f.get("signal_session"),PROVIDER)).fetchone()
  if not base or base[0]<=0 or (f.get("benchmark_pair")=="SPY_VOO" and (not voo_start or voo_start[0]<=0)):
   report["blocked"]+=1;continue
  obs=[]
  data=db.execute("""SELECT x.session,x.close,y.close,z.close FROM daily_bars x
   LEFT JOIN daily_bars y ON y.symbol='SPY' AND y.session=x.session AND y.provider=?
   LEFT JOIN daily_bars z ON z.symbol='VOO' AND z.session=x.session AND z.provider=?
   WHERE x.symbol=? AND x.provider=? AND x.session>? ORDER BY x.session""",
   (PROVIDER,PROVIDER,f["symbol"],PROVIDER,start)).fetchall()
  for day,close,spy,voo in data:
   if day>current.date().isoformat():continue
   if not close or not spy or close<=0 or spy<=0:continue
   if f.get("benchmark_pair")=="SPY_VOO" and (not voo or voo<=0):continue
   point={"date":day,"close":close,"benchmark_return":spy/base[0]-1,
          "price_source":f"{PROVIDER}:{f['symbol']}:{day}",
          "benchmark_source":f"{PROVIDER}:SPY:{day}"}
   if f.get("benchmark_pair")=="SPY_VOO":
    point.update(voo_return=voo/voo_start[0]-1,voo_source=f"{PROVIDER}:VOO:{day}")
   obs.append(point)
  result=score(db,fid,obs,iso(current))
  if result["status"]=="SCORED":report["outcomes_scored"]+=1
  elif result["status"]=="PENDING_HORIZON":report["pending"]+=1
  elif result["status"] not in ("EXISTS",):report["blocked"]+=1
 report["status"]="SHADOW_ACTIVE"
 report["summary"]=summary(db)
 return report

def main():
 root=Path("state");path=root/"marketwide.sqlite"
 if not path.exists():raise SystemExit("CONTINUITY_BLOCKED: missing marketwide DB")
 db=sqlite3.connect(path)
 current=utcnow()
 report=run(db,current,int(os.getenv("FORECAST_CANDIDATE_LIMIT","15")))
 db.commit()
 report["sqlite_integrity"]=db.execute("PRAGMA integrity_check").fetchone()[0]
 db.close()
 rid=current.strftime("%Y%m%dT%H%M%S%fZ")
 (root/f"forecast_receipt_{rid}.json").write_text(json.dumps(report,indent=2,sort_keys=True))
 print(json.dumps(report,indent=2))
if __name__=="__main__":main()
