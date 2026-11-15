"""Auditable, append-only cohort performance receipt from the actual shadow ledger."""
import datetime as dt
import hashlib
import json
import sqlite3
from pathlib import Path

def report(db):
 forecasts=db.execute("SELECT forecast_id,symbol,frozen_at,record_json,record_sha256 FROM shadow_forecasts ORDER BY frozen_at,forecast_id").fetchall()
 outcomes=db.execute("SELECT forecast_id,horizon_date,outcome_json,outcome_sha256 FROM shadow_outcomes ORDER BY forecast_id").fetchall()
 by_id={fid:json.loads(raw) for fid,_,raw,_ in outcomes}
 scored=[by_id[fid] for fid,_,_,_,_ in forecasts if fid in by_id]
 cohorts={}
 for fid,symbol,frozen,raw,digest in forecasts:
  key=frozen[:10]
  c=cohorts.setdefault(key,{"frozen":0,"scored":0,"pending":0,"net_returns":[],"excess_returns":[]})
  c["frozen"]+=1
  if fid in by_id:
   c["scored"]+=1;c["net_returns"].append(by_id[fid]["net_return"]);c["excess_returns"].append(by_id[fid]["excess_return"])
  else:c["pending"]+=1
 for c in cohorts.values():
  net=c.pop("net_returns");excess=c.pop("excess_returns")
  c["mean_net_return"]=sum(net)/len(net) if net else None
  c["mean_excess_return_vs_spy"]=sum(excess)/len(excess) if excess else None
  c["fraction_beating_spy"]=sum(x>0 for x in excess)/len(excess) if excess else None
 return {"forecasts_frozen":len(forecasts),"outcomes_scored":len(outcomes),
  "pending":len(forecasts)-len(outcomes),"mean_net_return":sum(x["net_return"] for x in scored)/len(scored) if scored else None,
  "mean_excess_return_vs_spy":sum(x["excess_return"] for x in scored)/len(scored) if scored else None,
  "fraction_beating_spy":sum(x["excess_return"]>0 for x in scored)/len(scored) if scored else None,
  "cohorts":cohorts,
  "forecasts":[{"id":fid,"symbol":sym,"frozen_at":frozen,"sha256":digest,"scored":fid in by_id} for fid,sym,frozen,raw,digest in forecasts],
  "caveat":"Shadow hypotheses use indicative prior closes, not executable fills. Small samples are not proof of predictive edge."}

def main():
 root=Path("state");path=root/"marketwide.sqlite"
 db=sqlite3.connect(path)
 result=report(db);db.close()
 now=dt.datetime.now(dt.timezone.utc)
 result["generated_at"]=now.isoformat()
 out=root/("performance_receipt_"+now.strftime("%Y%m%dT%H%M%S%fZ")+".json")
 out.write_text(json.dumps(result,indent=2,sort_keys=True))
 print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__":main()
