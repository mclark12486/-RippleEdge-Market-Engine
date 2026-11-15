"""Run bounded SEC-backed analysis of existing forensic queue in shadow mode.
All values are raw observations or conditional illustrations, never completed valuations.
"""
import datetime as dt,hashlib,json,os,sqlite3,time,urllib.request
from pathlib import Path
from research_models import cash_flow,dcf_scenarios,reconcile_balance,catalyst_score
UTC=dt.timezone.utc
def now():return dt.datetime.now(UTC).isoformat()
def get(url,agent):
 req=urllib.request.Request(url,headers={"User-Agent":agent,"Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=35) as r:return json.load(r)
def annual(tag_data,unit="USD"):
 vals={}
 for x in tag_data.get("units",{}).get(unit,[]):
  if x.get("form")!="10-K" or not x.get("start") or not x.get("end") or not isinstance(x.get("val"),(int,float)):continue
  try:days=(dt.date.fromisoformat(x["end"])-dt.date.fromisoformat(x["start"])).days
  except ValueError:continue
  if not 330<=days<=380:continue
  y=x["end"][:4]
  if y not in vals or (x.get("filed",""),x.get("accn",""))>(vals[y].get("filed",""),vals[y].get("accn","")):vals[y]=x
 return vals
def select(us,tags):
 for t in tags:
  v=annual(us.get(t,{}))
  if v:return {"tag":t,"observations":v}
 return {"tag":None,"observations":{}}
def main():
 root=Path("state");path=root/"forensic_shadow.sqlite"
 if not path.exists():raise SystemExit("CONTINUITY_BLOCKED")
 agent=os.getenv("SEC_USER_AGENT","")
 if "@" not in agent:raise SystemExit("SEC_USER_AGENT missing")
 db=sqlite3.connect(path)
 db.executescript("""
 CREATE TABLE IF NOT EXISTS analysis_evidence(id INTEGER PRIMARY KEY,symbol TEXT,run_id TEXT,observed_at TEXT,source_url TEXT,payload_json TEXT,classification TEXT);
 CREATE TABLE IF NOT EXISTS analysis_runs(run_id TEXT PRIMARY KEY,parent_run_id TEXT,started TEXT,ended TEXT,attempted INTEGER,verified INTEGER,errors_json TEXT);
 CREATE TABLE IF NOT EXISTS evidence_followups(id INTEGER PRIMARY KEY,symbol TEXT,run_id TEXT,created_at TEXT,missing_evidence TEXT,next_source TEXT,state TEXT);
 CREATE TRIGGER IF NOT EXISTS analysis_evidence_no_update BEFORE UPDATE ON analysis_evidence BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS analysis_evidence_no_delete BEFORE DELETE ON analysis_evidence BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS analysis_runs_no_update BEFORE UPDATE ON analysis_runs BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS analysis_runs_no_delete BEFORE DELETE ON analysis_runs BEGIN SELECT RAISE(ABORT,'immutable');END;
 """)
 parent=db.execute("SELECT run_id FROM analysis_runs ORDER BY started DESC LIMIT 1").fetchone()
 before=db.execute("SELECT COUNT(*) FROM analysis_evidence").fetchone()[0]
 rid=dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ");started=now()
 limit=max(1,min(int(os.getenv("ANALYSIS_BATCH_SIZE","150")),500))
 # SEC ticker-to-CIK mapping covers all mapped census companies, not just eight intake names.
 mapping=get("https://www.sec.gov/files/company_tickers.json",agent)
 ciks={str(v.get("ticker","")).upper():str(v["cik_str"]).zfill(10) for v in mapping.values() if v.get("ticker") and v.get("cik_str")}
 rows=db.execute("""SELECT q.symbol,q.etf FROM queue q
 WHERE NOT EXISTS(SELECT 1 FROM analysis_evidence a WHERE a.symbol=q.symbol)
 ORDER BY q.symbol""").fetchall()
 rows=[(symbol,etf,ciks.get(symbol)) for symbol,etf in rows if symbol in ciks or etf=="Y"][:limit]
 attempted=verified=primary_verified=deferred_funds=0;errors=[]
 for symbol,etf,cik in rows:
  attempted+=1
  url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json" if cik else ""
  observed=now()
  try:
   if etf=="Y":
    deferred_funds+=1
    result={"asset_type":"FUND","classification":"INSUFFICIENT_EVIDENCE","missing":["official dated holdings","NAV and premium/discount","expense ratio","flows","tracking error","look-through valuations"],"source_class":"UNVERIFIED"}
   elif not cik:
    result={"classification":"INSUFFICIENT_EVIDENCE","missing":["verified SEC CIK mapping"],"source_class":"UNVERIFIED"}
   else:
    data=get(url,agent);us=data.get("facts",{}).get("us-gaap",{})
    tags={"revenue":["RevenueFromContractWithCustomerExcludingAssessedTax","Revenues","SalesRevenueNet"],"cfo":["NetCashProvidedByUsedInOperatingActivities"],"capex":["PaymentsToAcquirePropertyPlantAndEquipment"],"net_income":["NetIncomeLoss"],"sbc":["ShareBasedCompensation"]}
    series={k:select(us,v) for k,v in tags.items()}
    years=sorted(set(series["cfo"]["observations"]) & set(series["capex"]["observations"]))
    fcf={y:cash_flow(series["cfo"]["observations"][y]["val"],series["capex"]["observations"][y]["val"])["fcf"] for y in years}
    last=sorted(fcf)[-3:];normalized=sum(fcf[y] for y in last)/len(last) if len(last)>=2 else None
    result={"asset_type":"COMPANY","classification":"INSUFFICIENT_EVIDENCE","entity":data.get("entityName"),"source_class":"SEC_PRIMARY_XBRL","series":{k:{"tag":v["tag"],"annual":{y:{"value":x["val"],"filed":x.get("filed"),"accession":x.get("accn"),"end":x["end"]} for y,x in v["observations"].items()}} for k,v in series.items()},"annual_fcf_proxy":fcf,"normalized_fcf_proxy":normalized,"scenario_status":"NOT_CALCULATED","reason":"Verified diluted shares, net debt, company-specific discount rates and maintenance capex are required before equity DCF","verified_equity_fair_value":None,"catalyst_rank":catalyst_score({"source_class":"primary_metadata"}),"setup":"NOT_VERIFIED"}
   db.execute("INSERT INTO analysis_evidence(symbol,run_id,observed_at,source_url,payload_json,classification) VALUES(?,?,?,?,?,?)",(symbol,rid,observed,url,json.dumps(result,sort_keys=True),"INSUFFICIENT_EVIDENCE"))
   db.execute("INSERT INTO evidence_followups(symbol,run_id,created_at,missing_evidence,next_source,state) VALUES(?,?,?,?,?,?)",(symbol,rid,now(),json.dumps(result.get("missing",["Issuer-specific debt, diluted shares, maintenance capex, full filings and catalyst verification"])),"SEC full-text filings / issuer IR / fund sponsor disclosures","OPEN"))
   verified+=1
   if result.get("source_class")=="SEC_PRIMARY_XBRL":primary_verified+=1
  except Exception as exc:errors.append({"symbol":symbol,"error":str(exc)[:150]})
  db.commit()
  time.sleep(.22)  # Bound request rate below SEC fair-access ceiling.
 db_count=db.execute("SELECT COUNT(*) FROM queue").fetchone()[0]
 after=db.execute("SELECT COUNT(*) FROM analysis_evidence").fetchone()[0]
 if after<before:raise SystemExit("CONTINUITY_BLOCKED: analysis evidence regressed")
 db.execute("INSERT INTO analysis_runs VALUES(?,?,?,?,?,?,?)",(rid,parent[0] if parent else None,started,now(),attempted,verified,json.dumps(errors)))
 db.commit();integrity=db.execute("PRAGMA integrity_check").fetchone()[0];db.close()
 receipt={"run_id":rid,"parent_run_id":parent[0] if parent else None,"attempted":attempted,"research_rows_appended":verified,"primary_xbrl_retrieved":primary_verified,"funds_deferred_no_primary":deferred_funds,"failed":len(errors),"errors":errors,"analysis_rows_before":before,"analysis_rows_after":after,"completed_equity_valuations":0,"verified_positive_catalysts":0,"coverage_denominator":db_count,"primary_xbrl_coverage_pct":round(100*primary_verified/max(1,db_count),4),"status":"PARTIAL_ANALYSIS","sqlite_integrity":integrity,"db_sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
 (root/("analysis_receipt_"+rid+".json")).write_text(json.dumps(receipt,indent=2))
 print(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
