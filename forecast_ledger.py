"""Append-only forecast ledger and evidence-scored outcomes.
Shadow research only. Never reconstruct predictions from later market data.
"""
import datetime as dt
import hashlib
import json
import sqlite3
from research_models import score_frozen_forecast, forecast_eligibility

def canonical(record):
 return json.dumps(record,sort_keys=True,separators=(",",":"),allow_nan=False)

def initialize(db):
 db.executescript("""
 CREATE TABLE IF NOT EXISTS shadow_forecasts(
  forecast_id TEXT PRIMARY KEY,symbol TEXT NOT NULL,frozen_at TEXT NOT NULL,
  evidence_cutoff TEXT NOT NULL,record_json TEXT NOT NULL,record_sha256 TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS shadow_outcomes(
  forecast_id TEXT NOT NULL,horizon_date TEXT NOT NULL,scored_at TEXT NOT NULL,
  outcome_json TEXT NOT NULL,outcome_sha256 TEXT NOT NULL,
  PRIMARY KEY(forecast_id,horizon_date));
 CREATE TRIGGER IF NOT EXISTS shadow_forecasts_no_update BEFORE UPDATE ON shadow_forecasts
 BEGIN SELECT RAISE(ABORT,'immutable forecast'); END;
 CREATE TRIGGER IF NOT EXISTS shadow_forecasts_no_delete BEFORE DELETE ON shadow_forecasts
 BEGIN SELECT RAISE(ABORT,'immutable forecast'); END;
 CREATE TRIGGER IF NOT EXISTS shadow_outcomes_no_update BEFORE UPDATE ON shadow_outcomes
 BEGIN SELECT RAISE(ABORT,'immutable outcome'); END;
 CREATE TRIGGER IF NOT EXISTS shadow_outcomes_no_delete BEFORE DELETE ON shadow_outcomes
 BEGIN SELECT RAISE(ABORT,'immutable outcome'); END;
 """)

def freeze(db,record):
 """Only freeze complete forecasts; idempotent replay, no retroactive overwrite."""
 initialize(db)
 required=("symbol","frozen_at","evidence_cutoff","entry_price","horizon_sessions","cost_bps","direction","benchmark")
 missing=[k for k in required if record.get(k) is None]
 if missing:return {"status":"REJECTED","missing":missing}
 if forecast_eligibility(record)["status"]!="ELIGIBLE_SHADOW":
  return {"status":"REJECTED","missing":forecast_eligibility(record)["missing"]}
 try:
  frozen=dt.datetime.fromisoformat(record["frozen_at"].replace("Z","+00:00"))
  cutoff=dt.datetime.fromisoformat(record["evidence_cutoff"].replace("Z","+00:00"))
  if frozen.tzinfo is None or cutoff.tzinfo is None or cutoff>frozen:
   raise ValueError("invalid timestamp or lookahead")
  if not record.get("source_receipts"):raise ValueError("no primary evidence receipts")
  raw=canonical(record)
  digest=hashlib.sha256(raw.encode()).hexdigest()
  fid=digest[:24]
  prior=db.execute("SELECT record_sha256 FROM shadow_forecasts WHERE forecast_id=?",(fid,)).fetchone()
  if prior:return {"status":"EXISTS" if prior[0]==digest else "COLLISION","forecast_id":fid}
  db.execute("INSERT INTO shadow_forecasts VALUES(?,?,?,?,?,?)",
   (fid,record["symbol"],record["frozen_at"],record["evidence_cutoff"],raw,digest))
  db.commit()
  return {"status":"FROZEN","forecast_id":fid,"sha256":digest}
 except (ValueError,TypeError,OverflowError) as e:return {"status":"REJECTED","reason":str(e)}

def score(db,forecast_id,observations,scored_at):
 """Score only actual frozen forecasts with sourced post-freeze observations."""
 initialize(db)
 row=db.execute("SELECT record_json FROM shadow_forecasts WHERE forecast_id=?",(forecast_id,)).fetchone()
 if not row:return {"status":"NOT_FOUND"}
 result=score_frozen_forecast(json.loads(row[0]),observations)
 if result["status"]!="SCORED":return result
 raw=canonical(result)
 digest=hashlib.sha256(raw.encode()).hexdigest()
 existing=db.execute("SELECT outcome_sha256 FROM shadow_outcomes WHERE forecast_id=? AND horizon_date=?",
  (forecast_id,result["horizon_date"])).fetchone()
 if existing:return {"status":"EXISTS" if existing[0]==digest else "CONFLICT_REVIEW_REQUIRED"}
 db.execute("INSERT INTO shadow_outcomes VALUES(?,?,?,?,?)",
  (forecast_id,result["horizon_date"],scored_at,raw,digest))
 db.commit()
 return dict(result,forecast_id=forecast_id,outcome_sha256=digest)

def summary(db):
 initialize(db)
 rows=db.execute("SELECT outcome_json FROM shadow_outcomes").fetchall()
 values=[json.loads(x[0]) for x in rows]
 if not values:return {"scored":0,"status":"NO_VERIFIED_OUTCOMES"}
 return {"scored":len(values),"mean_net_return":sum(x["net_return"] for x in values)/len(values),
 "mean_excess_return":sum(x["excess_return"] for x in values)/len(values),
 "positive_excess_fraction":sum(x["excess_return"]>0 for x in values)/len(values),
 "status":"DESCRIPTIVE_ONLY_NO_OUT_OF_SAMPLE_CLAIM"}
