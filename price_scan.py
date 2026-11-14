"""Optional bulk US stock/ETF daily OHLCV feed. Requires licensed Massive/Polygon grouped-bars API access."""
import datetime as dt, hashlib, json, os, sqlite3, sys, urllib.parse, urllib.request
from pathlib import Path
UTC=dt.timezone.utc
def now(): return dt.datetime.now(UTC).isoformat()
def main():
 root=Path("state");root.mkdir(exist_ok=True)
 dbpath=root/"marketwide.sqlite"
 if not dbpath.exists():raise SystemExit("CONTINUITY_BLOCKED: marketwide.sqlite missing")
 db=sqlite3.connect(dbpath)
 census=db.execute("SELECT symbol FROM securities WHERE last_seen=(SELECT MAX(last_seen) FROM securities)").fetchall()
 # Both listing directories share the same timestamp within a run; use latest run's observed census.
 if not census:raise SystemExit("CENSUS_BLOCKED: no current securities")
 symbols={s for (s,) in census};start=now();rid=dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
 db.executescript("""
 CREATE TABLE IF NOT EXISTS daily_bars(symbol TEXT,session TEXT,open REAL,high REAL,low REAL,close REAL,volume REAL,provider TEXT,first_seen TEXT,PRIMARY KEY(symbol,session,provider));
 CREATE TABLE IF NOT EXISTS price_runs(run_id TEXT PRIMARY KEY,checked_at TEXT,provider TEXT,session TEXT,requested INTEGER,returned INTEGER,matched INTEGER,missing INTEGER,unmatched INTEGER,status TEXT,receipt TEXT);
 CREATE TRIGGER IF NOT EXISTS price_runs_no_update BEFORE UPDATE ON price_runs BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS price_runs_no_delete BEFORE DELETE ON price_runs BEGIN SELECT RAISE(ABORT,'immutable');END;
 """)
 key=os.getenv("MASSIVE_API_KEY") or os.getenv("POLYGON_API_KEY")
 receipt={"run_id":rid,"checked_at":start,"provider":"Massive/Polygon grouped daily aggregates","census_requested":len(symbols),"endpoint":"https://api.massive.com/v2/aggs/grouped/locale/us/market/stocks/{date}","scope":"US equities and ETFs where provider has a daily bar; NOT intraday hourly quotes"}
 if not key:
  receipt.update({"status":"PRICE_FEED_BLOCKED","reason":"MASSIVE_API_KEY secret missing","provider_returned":0,"matched":0,"missing":len(symbols)})
 else:
  errors=[];bars=None;session=None
  for offset in range(1,7):
   day=dt.datetime.now(UTC).date()-dt.timedelta(days=offset)
   if day.weekday()>4:continue
   url=f"https://api.massive.com/v2/aggs/grouped/locale/us/market/stocks/{day}?adjusted=true"
   try:
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+key,"User-Agent":"RippleEdge market coverage research"})
    with urllib.request.urlopen(req,timeout=55) as resp:data=json.load(resp)
    if data.get("status") not in ("OK","DELAYED") or not isinstance(data.get("results"),list) or not data["results"]:raise ValueError("no valid grouped bars; status="+str(data.get("status")))
    bars=data["results"];session=str(day);break
   except Exception as e:errors.append({"session":str(day),"error":str(e)[:180]})
  if bars is None:
   receipt.update({"status":"PRICE_FEED_BLOCKED","reason":"No usable daily grouped result","errors":errors,"provider_returned":0,"matched":0,"missing":len(symbols)})
  else:
   matched=set();unmatched=0
   for b in bars:
    sym=b.get("T")
    if sym not in symbols:unmatched+=1;continue
    try:
     values=[float(b[k]) for k in ("o","h","l","c","v")]
     if any(x<0 for x in values):continue
     db.execute("INSERT OR IGNORE INTO daily_bars VALUES(?,?,?,?,?,?,?,?,?)",(sym,session,*values,"Massive/Polygon",now()))
     matched.add(sym)
    except (KeyError,ValueError,TypeError):continue
   db.commit()
   receipt.update({"status":"PARTIAL" if len(matched)!=len(symbols) else "DAILY_BAR_CENSUS_MATCHED","session":session,"provider_returned":len(bars),"matched":len(matched),"missing":len(symbols)-len(matched),"unmatched_provider_symbols":unmatched,"coverage_pct":round(100*len(matched)/len(symbols),4),"missing_examples":sorted(symbols-matched)[:40],"errors_prior_dates":errors})
 db.execute("INSERT INTO price_runs VALUES(?,?,?,?,?,?,?,?,?,?,?)",(rid,start,receipt["provider"],receipt.get("session"),len(symbols),receipt.get("provider_returned",0),receipt.get("matched",0),receipt.get("missing",len(symbols)),receipt.get("unmatched_provider_symbols",0),receipt["status"],json.dumps(receipt,sort_keys=True)))
 db.commit()
 integrity=db.execute("PRAGMA integrity_check").fetchone()[0]
 if integrity!="ok":raise RuntimeError("SQLite integrity failed")
 db.close()
 receipt["sqlite_integrity"]=integrity;receipt["db_sha256"]=hashlib.sha256(dbpath.read_bytes()).hexdigest()
 (root/("price_receipt_"+rid+".json")).write_text(json.dumps(receipt,indent=2))
 print(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
