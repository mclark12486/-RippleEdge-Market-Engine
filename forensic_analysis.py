"""RippleEdge forensic analysis v0.2: auditable raw-facts reconciliation, valuation scenarios,
SEC event intake, ETF evidence gates, prospective forecast infrastructure. SHADOW ONLY.
Never confuses a screening estimate with a completed forensic audit.
"""
import datetime as dt,hashlib,json,math,os,sqlite3,urllib.request
from pathlib import Path
UTC=dt.timezone.utc
def now():return dt.datetime.now(UTC).isoformat()
def fetch(url,agent):
 req=urllib.request.Request(url,headers={"User-Agent":agent,"Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=35) as r:return json.load(r)
def latest(us,tags,unit="USD",duration=None):
 observations=[]
 for tag in tags:
  for x in us.get(tag,{}).get("units",{}).get(unit,[]):
   if x.get("form") not in ("10-K","10-Q","20-F","40-F") or not isinstance(x.get("val"),(int,float)):continue
   if not x.get("filed") or not x.get("end"):continue
   if duration=="annual" and x.get("start"):
    days=(dt.date.fromisoformat(x["end"])-dt.date.fromisoformat(x["start"])).days
    if not 330<=days<=380:continue
   if duration=="instant" and x.get("start"):continue
   observations.append(dict(x,tag=tag))
 return max(observations,key=lambda x:(x["end"],x["filed"])) if observations else None
def historical(us,tags,unit="USD"):
 out={}
 for tag in tags:
  for x in us.get(tag,{}).get("units",{}).get(unit,[]):
   if x.get("form")!="10-K" or not x.get("start") or not x.get("end"):continue
   days=(dt.date.fromisoformat(x["end"])-dt.date.fromisoformat(x["start"])).days
   if not 330<=days<=380 or not isinstance(x.get("val"),(int,float)):continue
   yr=x["end"][:4];cur=out.get(yr)
   if cur is None or (x.get("filed",""),x.get("end",""))>(cur.get("filed",""),cur.get("end","")):out[yr]=dict(x,tag=tag)
 return out
def scenario(fcf,growth,discount,terminal,years=5):
 if discount<=terminal or fcf<=0:return None
 cash=fcf;pv=0
 for i in range(1,years+1):
  cash*=1+growth;pv+=cash/(1+discount)**i
 pv+=cash*(1+terminal)/(discount-terminal)/(1+discount)**years
 return pv
def main():
 root=Path("state");dbpath=root/"forensic_shadow.sqlite";market=root/"marketwide.sqlite"
 if not dbpath.exists() or not market.exists():raise SystemExit("CONTINUITY_BLOCKED: upstream databases missing")
 agent=os.getenv("SEC_USER_AGENT","")
 if "@" not in agent:raise SystemExit("SEC_USER_AGENT required")
 db=sqlite3.connect(dbpath)
 db.executescript("""
 CREATE TABLE IF NOT EXISTS analyses(id INTEGER PRIMARY KEY,symbol TEXT,run_id TEXT,observed_at TEXT,source_url TEXT,analysis_json TEXT,status TEXT);
 CREATE TABLE IF NOT EXISTS catalyst_events(id INTEGER PRIMARY KEY,symbol TEXT,run_id TEXT,observed_at TEXT,filing_date TEXT,form TEXT,accession TEXT,primary_url TEXT,signal TEXT,confidence TEXT,notes TEXT,UNIQUE(symbol,accession,form));
 CREATE TABLE IF NOT EXISTS forecast_freezes(id INTEGER PRIMARY KEY,symbol TEXT,created_at TEXT,evidence_cutoff TEXT,entry_low REAL,entry_high REAL,direction TEXT,horizon_sessions INTEGER,target REAL,invalidation REAL,benchmark TEXT,cost_bps REAL,source_analysis_id INTEGER,status TEXT DEFAULT 'RESEARCH_ONLY');
 CREATE TABLE IF NOT EXISTS forecast_scores(id INTEGER PRIMARY KEY,forecast_id INTEGER,asof TEXT,horizon_sessions INTEGER,fill_price REAL,exit_price REAL,benchmark_return REAL,net_return REAL,drawdown REAL,source_url TEXT,notes TEXT,UNIQUE(forecast_id,horizon_sessions));
 CREATE TABLE IF NOT EXISTS analysis_runs(run_id TEXT PRIMARY KEY,parent_run_id TEXT,started TEXT,ended TEXT,attempted INTEGER,financial_verified INTEGER,events_seen INTEGER,valuations_screened INTEGER,etf_deferred INTEGER,receipt_json TEXT);
 CREATE TRIGGER IF NOT EXISTS analyses_immutable_update BEFORE UPDATE ON analyses BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS analyses_immutable_delete BEFORE DELETE ON analyses BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS forecasts_immutable_update BEFORE UPDATE ON forecast_freezes BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS forecasts_immutable_delete BEFORE DELETE ON forecast_freezes BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS scores_immutable_update BEFORE UPDATE ON forecast_scores BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS scores_immutable_delete BEFORE DELETE ON forecast_scores BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS analysis_runs_immutable_update BEFORE UPDATE ON analysis_runs BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS analysis_runs_immutable_delete BEFORE DELETE ON analysis_runs BEGIN SELECT RAISE(ABORT,'immutable');END;
 """)
 prior=db.execute("SELECT run_id FROM analysis_runs ORDER BY started DESC LIMIT 1").fetchone()
 run=dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ");started=now()
 # Round-robin only previously SEC-verified companies, not merely listed securities.
 rows=db.execute("""SELECT q.symbol,q.etf,json_extract(e.findings_json,'$.cik') AS cik
 FROM queue q JOIN evidence e ON e.id=(SELECT MAX(id) FROM evidence WHERE symbol=q.symbol)
 WHERE cik IS NOT NULL AND NOT EXISTS(SELECT 1 FROM analyses a WHERE a.symbol=q.symbol)
 ORDER BY e.id LIMIT ?""",(max(1,min(int(os.getenv("ANALYSIS_BATCH_SIZE","5")),15)),)).fetchall()
 errors=[];attempted=verified=events=screened=etf_deferred=0
 for symbol,etf,cik in rows:
  attempted+=1;url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json";observed=now()
  try:
   if etf=="Y":
    etf_deferred+=1
    result={"classification":"INSUFFICIENT_EVIDENCE","asset_type":"ETF","requirements":["dated official holdings and weights","NAV and premium/discount","fees, flows, liquidity, tracking error","look-through holdings valuation"],"valuation":None}
   else:
    data=fetch(url,agent);us=data.get("facts",{}).get("us-gaap",{})
    groups={
     "revenue":["RevenueFromContractWithCustomerExcludingAssessedTax","Revenues","SalesRevenueNet"],
     "net_income":["NetIncomeLoss"],"operating_cash":["NetCashProvidedByUsedInOperatingActivities"],
     "capex":["PaymentsToAcquirePropertyPlantAndEquipment"],
     "assets":["Assets"],"liabilities":["Liabilities"],"equity":["StockholdersEquity"],
     "receivables":["AccountsReceivableNetCurrent"],"inventory":["InventoryNet"],
     "debt":["LongTermDebtCurrent","LongTermDebtNoncurrent"],"stock_comp":["ShareBasedCompensation"],
     "cash":["CashAndCashEquivalentsAtCarryingValue"]}
    series={k:historical(us,v) for k,v in groups.items()}
    annual={k:{y:{"value":x["val"],"filed":x["filed"],"form":x["form"],"accession":x.get("accn"),"end":x["end"]} for y,x in d.items()} for k,d in series.items()}
    # Annual matching periods only; no mixing instant and flow figures.
    common=sorted(set(series["operating_cash"]) & set(series["capex"]))
    fcf={y:series["operating_cash"][y]["val"]-series["capex"][y]["val"] for y in common}
    years=sorted(fcf)[-3:]
    normalized=sum(fcf[y] for y in years)/len(years) if years else None
    scenarios=None;reason="Annual cash flow/capex missing or nonpositive"
    if normalized is not None and normalized>0 and len(years)>=2:
     scenarios={name:scenario(normalized,g,r,t) for name,g,r,t in [("bear",-0.03,0.14,0.015),("base",0.04,0.11,0.025),("bull",0.10,0.09,0.03)]}
     reason="Illustrative enterprise operating cash-flow proxy; NOT equity fair value. Requires debt/cash, SBC, dilution, capex normalization and issuer-specific discount rates."
     screened+=1
    result={"asset_type":"COMPANY","entity":data.get("entityName"),"classification":"INSUFFICIENT_EVIDENCE","annual_raw_facts":annual,"annual_fcf_proxy":fcf,"normalized_fcf_proxy":normalized,"historical_years":years,"illustrative_enterprise_scenarios":scenarios,"scenario_assumptions":{"bear":{"growth":-0.03,"discount":0.14,"terminal":0.015},"base":{"growth":0.04,"discount":0.11,"terminal":0.025},"bull":{"growth":0.10,"discount":0.09,"terminal":0.03}},"valuation_caveat":reason,"verified_equity_fair_value":None,"price_to_value":None,"setup":"NOT_VERIFIED","required_next":["Reconcile restatements and segment disclosures","Bridge enterprise to equity and verify shares/dilution","Assess debt maturities, leases, concentration, working capital, maintenance capex","Use issuer-specific peer and discount-rate assumptions","Verify upcoming catalysts from original documents"]}
   db.execute("INSERT INTO analyses(symbol,run_id,observed_at,source_url,analysis_json,status) VALUES(?,?,?,?,?,?)",(symbol,run,observed,url,json.dumps(result,sort_keys=True),"SCREEN_ONLY"))
   verified+=1
   # SEC submissions metadata is a discovery pointer, not verification of filing full text.
   if cik and etf!="Y":
    suburl=f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
     sub=fetch(suburl,agent).get("filings",{}).get("recent",{})
     for i,form in enumerate(sub.get("form",[])[:40]):
      if form not in ("8-K","6-K","10-Q","10-K","S-1","424B5"):continue
      acc=sub.get("accessionNumber",[])[i];date=sub.get("filingDate",[])[i]
      doc=sub.get("primaryDocument",[])[i];link=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-','')}/{doc}"
      db.execute("INSERT OR IGNORE INTO catalyst_events(symbol,run_id,observed_at,filing_date,form,accession,primary_url,signal,confidence,notes) VALUES(?,?,?,?,?,?,?,?,?,?)",(symbol,run,now(),date,form,acc,link,"FILING_DISCOVERY_ONLY","UNVERIFIED","Filing metadata discovered; full document NOT read; no positive catalyst inferred"))
      events+=1
    except Exception as exc:errors.append({"symbol":symbol,"stage":"SEC submissions","error":str(exc)[:120]})
  except Exception as exc:errors.append({"symbol":symbol,"stage":"analysis","error":str(exc)[:150]})
  db.commit()
 receipt={"run_id":run,"parent_run_id":prior[0] if prior else None,"started":started,"ended":now(),"attempted":attempted,"financial_sources_retrieved":verified,"filing_metadata_observed":events,"illustrative_scenario_screens":screened,"etf_evidence_deferred":etf_deferred,"verified_equity_valuations":0,"verified_catalyst_impacts":0,"prospective_forecasts_frozen":0,"forecast_scores_added":0,"errors":errors,"status":"SHADOW_PARTIAL","warning":"Illustrative screens are not issuer-specific forensic equity valuations. SEC filing metadata is not full-document catalyst verification."}
 db.execute("INSERT INTO analysis_runs VALUES(?,?,?,?,?,?,?,?,?,?)",(run,prior[0] if prior else None,started,now(),attempted,verified,events,screened,etf_deferred,json.dumps(receipt,sort_keys=True)))
 db.commit();integrity=db.execute("PRAGMA integrity_check").fetchone()[0];db.close()
 if integrity!="ok":raise SystemExit("INTEGRITY_BLOCKED: "+integrity)
 receipt["sqlite_integrity"]=integrity;receipt["db_sha256"]=hashlib.sha256(dbpath.read_bytes()).hexdigest()
 (root/("forensic_analysis_receipt_"+run+".json")).write_text(json.dumps(receipt,indent=2))
 print(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
