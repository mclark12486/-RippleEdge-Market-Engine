"""RippleEdge market-wide breadth screening using ALL available grouped daily bars.
No per-symbol API calls. Unobserved symbols remain explicit missing coverage.
"""
import datetime as dt,hashlib,json,sqlite3
from pathlib import Path
UTC=dt.timezone.utc
def main():
 root=Path("state");path=root/"marketwide.sqlite"
 if not path.exists():raise SystemExit("CONTINUITY_BLOCKED: marketwide database missing")
 db=sqlite3.connect(path)
 db.executescript("""
 CREATE TABLE IF NOT EXISTS breadth_runs(run_id TEXT PRIMARY KEY,checked_at TEXT,session TEXT,census INTEGER,matched INTEGER,missing INTEGER,price_signals INTEGER,receipt TEXT);
 CREATE TABLE IF NOT EXISTS breadth_signals(id INTEGER PRIMARY KEY,symbol TEXT,run_id TEXT,session TEXT,signal TEXT,metric REAL,baseline_sessions INTEGER,observed_at TEXT);
 CREATE TRIGGER IF NOT EXISTS breadth_runs_no_update BEFORE UPDATE ON breadth_runs BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS breadth_runs_no_delete BEFORE DELETE ON breadth_runs BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS breadth_signals_no_update BEFORE UPDATE ON breadth_signals BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS breadth_signals_no_delete BEFORE DELETE ON breadth_signals BEGIN SELECT RAISE(ABORT,'immutable');END;
 """)
 rid=dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ");observed=dt.datetime.now(UTC).isoformat()
 census={r[0] for r in db.execute("SELECT symbol FROM securities WHERE last_seen=(SELECT MAX(last_seen) FROM securities)")}
 if not census:raise SystemExit("CENSUS_BLOCKED")
 session=db.execute("SELECT MAX(session) FROM daily_bars WHERE provider='Massive/Polygon'").fetchone()[0]
 if not session:
  receipt={"run_id":rid,"checked_at":observed,"session":None,"census":len(census),
   "bulk_bar_matched":0,"missing":len(census),"coverage_pct":0,"signal_count":0,
   "status":"BULK_PRICE_BLOCKED","reason":"No licensed daily bars; no signals generated"}
  db.execute("INSERT INTO breadth_runs VALUES(?,?,?,?,?,?,?,?)",(rid,observed,None,len(census),0,len(census),0,json.dumps(receipt,sort_keys=True)))
  db.commit()
  receipt["sqlite_integrity"]=db.execute("PRAGMA integrity_check").fetchone()[0]
  db.close()
  receipt["db_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
  (root/("breadth_receipt_"+rid+".json")).write_text(json.dumps(receipt,indent=2))
  print(json.dumps(receipt,indent=2))
  return
 rows=db.execute("""SELECT symbol,close,volume,high,low FROM daily_bars WHERE session=? AND provider='Massive/Polygon'""",(session,)).fetchall()
 matched=set();signals=0
 for symbol,close,volume,high,low in rows:
  if symbol not in census:continue
  matched.add(symbol)
  hist=db.execute("SELECT close,volume FROM daily_bars WHERE symbol=? AND provider='Massive/Polygon' AND session<? ORDER BY session DESC LIMIT 20",(symbol,session)).fetchall()
  if len(hist)<5:continue
  avgvol=sum(x[1] for x in hist)/len(hist)
  prevclose=hist[0][0]
  if prevclose<=0 or avgvol<=0:continue
  change=close/prevclose-1;ratio=volume/avgvol
  # Signals only when historical observations exist. No implication of a catalyst.
  for label,metric,trigger in (("PRICE_CHANGE",change,abs(change)>=0.08),("RELATIVE_VOLUME",ratio,ratio>=3)):
   if trigger:
    db.execute("INSERT INTO breadth_signals(symbol,run_id,session,signal,metric,baseline_sessions,observed_at) VALUES(?,?,?,?,?,?,?)",(symbol,rid,session,label,metric,len(hist),observed));signals+=1
 receipt={"run_id":rid,"checked_at":observed,"session":session,"census":len(census),"bulk_bar_matched":len(matched),"missing":len(census-matched),"coverage_pct":round(100*len(matched)/len(census),4),"signal_count":signals,"scope":"all census symbols matched to provider daily bars; not hourly quotes, fundamental audits, or catalyst verification","history_requirement":"5 prior daily bars; newly connected feeds may produce zero signals","status":"PARTIAL" if len(matched)<len(census) else "DAILY_BAR_CENSUS_MATCHED"}
 db.execute("INSERT INTO breadth_runs VALUES(?,?,?,?,?,?,?,?)",(rid,observed,session,len(census),len(matched),len(census-matched),signals,json.dumps(receipt,sort_keys=True)))
 db.commit();receipt["sqlite_integrity"]=db.execute("PRAGMA integrity_check").fetchone()[0];db.close()
 receipt["db_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
 (root/("breadth_receipt_"+rid+".json")).write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
