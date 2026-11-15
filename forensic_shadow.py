"""RippleEdge shadow forensic intake v0.1. Research-only; never emits trades or fair values without models."""
import datetime as dt, hashlib, json, os, sqlite3, time, urllib.request
from pathlib import Path
UTC=dt.timezone.utc
def stamp(): return dt.datetime.now(UTC).isoformat()
def fetch(url,agent):
 req=urllib.request.Request(url,headers={"User-Agent":agent,"Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
def main():
 root=Path("state"); dbpath=root/"forensic_shadow.sqlite"; market=root/"marketwide.sqlite"
 if not market.exists():raise SystemExit("CONTINUITY_BLOCKED: marketwide census missing")
 agent=os.getenv("SEC_USER_AGENT","")
 if "@" not in agent:raise SystemExit("SEC_USER_AGENT missing")
 source=sqlite3.connect(f"file:{market}?mode=ro",uri=True)
 names=source.execute("SELECT symbol,name,etf,venue FROM securities WHERE last_seen=(SELECT MAX(last_seen) FROM securities) ORDER BY symbol").fetchall()
 source.close()
 if not names:raise SystemExit("CENSUS_BLOCKED")
 if (root/"forensic_shadow_initialized").exists() and not dbpath.exists():raise SystemExit("CONTINUITY_BLOCKED: forensic state missing")
 db=sqlite3.connect(dbpath)
 db.executescript("""
 CREATE TABLE IF NOT EXISTS queue(symbol TEXT PRIMARY KEY,name TEXT,etf TEXT,venue TEXT,first_seen TEXT,last_seen TEXT,review_state TEXT DEFAULT 'QUEUED',last_review TEXT);
 CREATE TABLE IF NOT EXISTS evidence(id INTEGER PRIMARY KEY,symbol TEXT,run_id TEXT,observed_at TEXT,source_url TEXT,source_class TEXT,filing_date TEXT,findings_json TEXT,review_state TEXT);
 CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY,started TEXT,ended TEXT,census INTEGER,attempted INTEGER,verified INTEGER,failed INTEGER,deferred INTEGER,receipt_json TEXT);
 CREATE TRIGGER IF NOT EXISTS evidence_no_update BEFORE UPDATE ON evidence BEGIN SELECT RAISE(ABORT,'immutable evidence');END;
 CREATE TRIGGER IF NOT EXISTS evidence_no_delete BEFORE DELETE ON evidence BEGIN SELECT RAISE(ABORT,'immutable evidence');END;
 CREATE TRIGGER IF NOT EXISTS runs_no_update BEFORE UPDATE ON runs BEGIN SELECT RAISE(ABORT,'immutable run');END;
 CREATE TRIGGER IF NOT EXISTS runs_no_delete BEFORE DELETE ON runs BEGIN SELECT RAISE(ABORT,'immutable run');END;
 """)
 previous=db.execute("SELECT run_id,verified FROM runs ORDER BY started DESC LIMIT 1").fetchone()
 previous_evidence=db.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
 if previous and previous_evidence==0 and previous[1]>0:raise SystemExit("CONTINUITY_BLOCKED: historical evidence missing")
 start=stamp();rid=dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
 for symbol,name,etf,venue in names:
  db.execute("INSERT INTO queue(symbol,name,etf,venue,first_seen,last_seen) VALUES(?,?,?,?,?,?) ON CONFLICT(symbol) DO UPDATE SET name=excluded.name,etf=excluded.etf,venue=excluded.venue,last_seen=excluded.last_seen",(symbol,name,etf,venue,start,start))
 db.commit()
 # Only SEC CIK mappings can support companyfacts; ETFs/foreign issuers may require distinct primary sources.
 mapping_url="https://www.sec.gov/files/company_tickers.json"
 errors=[];mapped={}
 try:
  data=fetch(mapping_url,agent)
  mapped={str(v.get("ticker","")).upper():str(v["cik_str"]).zfill(10) for v in data.values() if v.get("ticker") and v.get("cik_str")}
 except Exception as exc:errors.append({"source":mapping_url,"error":str(exc)[:160]})
 limit=max(1,min(int(os.getenv("FORENSIC_BATCH_SIZE","8")),30))
 rows=db.execute("SELECT symbol,etf FROM queue WHERE review_state='QUEUED' ORDER BY symbol LIMIT ?",(limit*15,)).fetchall()
 candidates=[(s,e) for s,e in rows if s in mapped][:limit]
 attempted=verified=failed=0
 for symbol,etf in candidates:
  attempted+=1;url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{mapped[symbol]}.json";observed=stamp()
  try:
   facts=fetch(url,agent);us=facts.get("facts",{}).get("us-gaap",{})
   tags=["Revenues","RevenueFromContractWithCustomerExcludingAssessedTax","NetIncomeLoss","NetCashProvidedByUsedInOperatingActivities","PaymentsToAcquirePropertyPlantAndEquipment","Assets","Liabilities","StockholdersEquity","CommonStockSharesOutstanding"]
   observed_tags={k:len(us.get(k,{}).get("units",{})) for k in tags if k in us}
   # Preserve actual latest XBRL observations, including period, filing, unit and form.
   # These are raw observations, NOT reconciled financials or a valuation.
   raw_latest={}
   for tag in tags:
    for unit,entries in us.get(tag,{}).get("units",{}).items():
     eligible=[x for x in entries if x.get("filed") and x.get("end") and isinstance(x.get("val"),(int,float))]
     if eligible:
      x=max(eligible,key=lambda x:(x.get("filed",""),x.get("end","")))
      raw_latest[tag]={"value":x["val"],"unit":unit,"start":x.get("start"),"end":x["end"],"filed":x["filed"],"form":x.get("form"),"accession":x.get("accn")}
      break
   finding={"cik":mapped[symbol],"entity":facts.get("entityName"),"present_tags":observed_tags,"raw_latest_observations":raw_latest,"tag_count":len(us),"limitations":["Raw XBRL availability only; no reconciled financial statements","No DCF or bear/base/bull valuation","No independently verified forward catalyst","No price-to-value or executable setup"],"classification":"INSUFFICIENT_EVIDENCE"}
   db.execute("INSERT INTO evidence(symbol,run_id,observed_at,source_url,source_class,filing_date,findings_json,review_state) VALUES(?,?,?,?,?,?,?,?)",(symbol,rid,observed,url,"SEC_PRIMARY_XBRL",None,json.dumps(finding,sort_keys=True),"PARTIAL"))
   db.execute("UPDATE queue SET review_state='PARTIAL',last_review=? WHERE symbol=?",(observed,symbol))
   verified+=1
  except Exception as exc:
   failed+=1;errors.append({"symbol":symbol,"source":url,"error":str(exc)[:160]})
  db.commit();time.sleep(.15)
 if previous and db.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]<previous_evidence:raise SystemExit("CONTINUITY_BLOCKED: evidence count regressed")
 counts=dict(db.execute("SELECT review_state,COUNT(*) FROM queue GROUP BY review_state").fetchall())
 receipt={"run_id":rid,"parent_run_id":previous[0] if previous else None,"prior_evidence_rows":previous_evidence,"evidence_rows_after":db.execute("SELECT COUNT(*) FROM evidence").fetchone()[0],"started":start,"ended":stamp(),"execution":"GitHub Actions shadow","census":len(names),"queued_total":sum(counts.values()),"attempted":attempted,"primary_verified":verified,"failed":failed,"deferred":len(names)-attempted,"states":counts,"source_mapping":mapping_url,"mapping_count":len(mapped),"errors":errors,"valuation_completed":0,"forecast_scored":0,"status":"PARTIAL_RESEARCH_ONLY","warning":"SEC XBRL tag presence is not a forensic audit or catalyst scan"}
 db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?)",(rid,start,stamp(),len(names),attempted,verified,failed,len(names)-attempted,json.dumps(receipt,sort_keys=True)))
 db.commit();receipt["sqlite_integrity"]=db.execute("PRAGMA integrity_check").fetchone()[0];db.close()
 (root/"forensic_shadow_initialized").write_text(rid)
 receipt["db_sha256"]=hashlib.sha256(dbpath.read_bytes()).hexdigest()
 (root/("forensic_shadow_receipt_"+rid+".json")).write_text(json.dumps(receipt,indent=2))
 print(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
