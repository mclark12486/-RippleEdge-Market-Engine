"""Incremental grouped-daily history backfill for market-wide signal baselines.
Fetches up to 3 missing trading sessions per execution; never treats missing as checked.
"""
import datetime as dt,hashlib,json,os,sqlite3,urllib.request
from pathlib import Path
UTC=dt.timezone.utc
def now():return dt.datetime.now(UTC).isoformat()
def main():
 root=Path("state");path=root/"marketwide.sqlite"
 if not path.exists():raise SystemExit("CONTINUITY_BLOCKED")
 key=os.getenv("MASSIVE_API_KEY") or os.getenv("POLYGON_API_KEY")
 if not key:raise SystemExit("HISTORY_BLOCKED: missing licensed market data key")
 db=sqlite3.connect(path)
 db.execute("""CREATE TABLE IF NOT EXISTS history_runs(run_id TEXT PRIMARY KEY,checked_at TEXT,attempted_dates TEXT,successful_dates TEXT,errors TEXT,receipt TEXT)""")
 db.executescript("""
 CREATE TRIGGER IF NOT EXISTS history_runs_no_update BEFORE UPDATE ON history_runs BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS history_runs_no_delete BEFORE DELETE ON history_runs BEGIN SELECT RAISE(ABORT,'immutable');END;
 """)
 census={x[0] for x in db.execute("SELECT symbol FROM securities WHERE last_seen=(SELECT MAX(last_seen) FROM securities)")}
 latest=db.execute("SELECT MAX(session) FROM daily_bars WHERE provider='Massive/Polygon'").fetchone()[0]
 if not latest or not census:raise SystemExit("HISTORY_BLOCKED: missing current daily bars or census")
 rid=dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
 # Work backward from the most recent session; do not repeat previously attempted dates without explicit retry.
 prior=set()
 for (dates,) in db.execute("SELECT attempted_dates FROM history_runs"):
  prior.update(json.loads(dates))
 dates=[];d=dt.date.fromisoformat(latest)-dt.timedelta(days=1)
 while len(dates)<3 and d>=dt.date.fromisoformat(latest)-dt.timedelta(days=45):
  if d.weekday()<5 and str(d) not in prior:dates.append(str(d))
  d-=dt.timedelta(days=1)
 results=[];errors=[]
 for day in dates:
  url=f"https://api.massive.com/v2/aggs/grouped/locale/us/market/stocks/{day}?adjusted=true"
  try:
   req=urllib.request.Request(url,headers={"Authorization":"Bearer "+key,"User-Agent":"RippleEdge market history research"})
   with urllib.request.urlopen(req,timeout=65) as resp:data=json.load(resp)
   bars=data.get("results")
   if data.get("status") not in ("OK","DELAYED") or not isinstance(bars,list) or not bars:raise ValueError("No usable grouped aggregates")
   seen=set();inserted=0
   for b in bars:
    symbol=b.get("T")
    if symbol not in census or symbol in seen:continue
    try:
     values=[float(b[k]) for k in ("o","h","l","c","v")]
     if any(v<0 for v in values):continue
    except (KeyError,ValueError,TypeError):continue
    seen.add(symbol)
    inserted+=db.execute("INSERT OR IGNORE INTO daily_bars VALUES(?,?,?,?,?,?,?,?,?)",(symbol,day,*values,"Massive/Polygon",now())).rowcount
   db.commit()
   results.append({"session":day,"provider_returned":len(bars),"matched":len(seen),"inserted":inserted,"missing":len(census-seen)})
  except Exception as exc:errors.append({"session":day,"error":str(exc)[:180]})
 receipt={"run_id":rid,"checked_at":now(),"latest_session":latest,"attempted_dates":dates,"successful_dates":results,"errors":errors,"census":len(census),"historical_sessions_available":db.execute("SELECT COUNT(DISTINCT session) FROM daily_bars WHERE provider='Massive/Polygon'").fetchone()[0],"status":"PARTIAL" if errors else "BACKFILL_PROGRESS","scope":"Historical grouped daily bars, not intraday or forensic valuations"}
 db.execute("INSERT INTO history_runs VALUES(?,?,?,?,?,?)",(rid,receipt["checked_at"],json.dumps(dates),json.dumps(results),json.dumps(errors),json.dumps(receipt,sort_keys=True)))
 db.commit();receipt["sqlite_integrity"]=db.execute("PRAGMA integrity_check").fetchone()[0];db.close()
 receipt["db_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
 (root/("history_receipt_"+rid+".json")).write_text(json.dumps(receipt,indent=2))
 print(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
