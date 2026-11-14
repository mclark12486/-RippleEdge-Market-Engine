"""RippleEdge SEC filing intake. SEC coverage is NOT full exchange coverage."""
import argparse, datetime as dt, hashlib, json, os, sqlite3, time, urllib.request
from pathlib import Path
UTC=dt.timezone.utc
def now(): return dt.datetime.now(UTC).isoformat()
def fetch(url,agent):
    req=urllib.request.Request(url,headers={"User-Agent":agent,"Accept-Encoding":"identity"})
    with urllib.request.urlopen(req,timeout=30) as response: return response.read()
def initialize(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS universe(cik TEXT PRIMARY KEY,ticker TEXT,name TEXT,first_seen TEXT,last_seen TEXT);
    CREATE TABLE IF NOT EXISTS checks(run_id TEXT,cik TEXT,status TEXT,checked_at TEXT,source TEXT,detail TEXT,PRIMARY KEY(run_id,cik));
    CREATE TABLE IF NOT EXISTS filings(cik TEXT,accession TEXT,form TEXT,filed TEXT,document TEXT,first_seen TEXT,PRIMARY KEY(cik,accession));
    CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY,started TEXT,ended TEXT,universe_count INTEGER,checked INTEGER,failed INTEGER,new_filings INTEGER,coverage_pct REAL,notes TEXT);
    CREATE TRIGGER IF NOT EXISTS finalized_runs_no_update BEFORE UPDATE ON runs WHEN OLD.ended IS NOT NULL BEGIN SELECT RAISE(ABORT,'immutable run'); END;
    CREATE TRIGGER IF NOT EXISTS runs_no_delete BEFORE DELETE ON runs BEGIN SELECT RAISE(ABORT,'immutable run'); END;
    CREATE TRIGGER IF NOT EXISTS filings_no_delete BEFORE DELETE ON filings BEGIN SELECT RAISE(ABORT,'immutable filing'); END;
    """)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",default="state/latest.sqlite")
    p.add_argument("--agent",default=os.getenv("SEC_USER_AGENT",""))
    p.add_argument("--max-checks",type=int,default=0)
    p.add_argument("--delay",type=float,default=.15)
    a=p.parse_args()
    if "@" not in a.agent: p.error("Set SEC_USER_AGENT to a truthful contact email")
    path=Path(a.db);path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path);initialize(db)
    started=now();rid=dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    try:
        source="https://www.sec.gov/files/company_tickers.json"
        raw=json.loads(fetch(source,a.agent))
        tickers={str(v["cik_str"]).zfill(10):(v["ticker"],v["title"]) for v in raw.values()}
        for cik,(ticker,name) in tickers.items():
            db.execute("INSERT INTO universe VALUES(?,?,?,?,?) ON CONFLICT(cik) DO UPDATE SET ticker=excluded.ticker,name=excluded.name,last_seen=excluded.last_seen",(cik,ticker,name,started,started))
        db.commit()
        candidates=db.execute("SELECT u.cik FROM universe u LEFT JOIN (SELECT cik,MAX(checked_at) last_check FROM checks GROUP BY cik) c ON u.cik=c.cik ORDER BY c.last_check IS NOT NULL,c.last_check,u.cik").fetchall()
        if a.max_checks: candidates=candidates[:a.max_checks]
        checked=failed=new_filings=0
        for (cik,) in candidates:
            url="https://data.sec.gov/submissions/CIK"+cik+".json"
            try:
                data=json.loads(fetch(url,a.agent));recent=data.get("filings",{}).get("recent",{})
                for accession,form,filed,doc in zip(recent.get("accessionNumber",[]),recent.get("form",[]),recent.get("filingDate",[]),recent.get("primaryDocument",[])):
                    new_filings+=db.execute("INSERT OR IGNORE INTO filings VALUES(?,?,?,?,?,?)",(cik,accession,form,filed,doc,now())).rowcount
                db.execute("INSERT INTO checks VALUES(?,?,?,?,?,?)",(rid,cik,"OK",now(),url,None));checked+=1
            except Exception as e:
                db.execute("INSERT INTO checks VALUES(?,?,?,?,?,?)",(rid,cik,"FAILED",now(),url,str(e)[:300]));failed+=1
            db.commit();time.sleep(a.delay)
        total=len(tickers)
        db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?)",(rid,started,now(),total,checked,failed,new_filings,100*checked/total if total else 0,"SEC submissions only; not full market or valuation"))
        db.commit()
        integrity=db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity!="ok": raise RuntimeError("SQLite integrity failure: "+integrity)
        db.close()
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        receipt={"run_id":rid,"started":started,"ended":now(),"universe_source":source,"universe_count":total,"checked":checked,"failed":failed,"unchecked":total-checked-failed,"new_filing_records":new_filings,"coverage_pct":100*checked/total if total else 0,"coverage_scope":"SEC CIK submissions only","full_market_hourly_coverage":"BLOCKED","database_sha256":sha,"integrity_check":integrity}
        out=path.parent/("receipt_"+rid+".json");out.write_text(json.dumps(receipt,indent=2))
        print(json.dumps(receipt,indent=2))
    finally:
        try: db.close()
        except Exception: pass
if __name__=="__main__": main()
