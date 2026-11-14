"""RippleEdge exchange-wide census + SEC index intake. No investment forecasts."""
import csv,datetime as dt,hashlib,io,json,os,sqlite3,sys,urllib.request
from pathlib import Path
UTC=dt.timezone.utc
def now():return dt.datetime.now(UTC).isoformat()
def get(url,agent):
 req=urllib.request.Request(url,headers={"User-Agent":agent,"Accept-Encoding":"gzip, deflate","Accept":"text/plain,application/json,*/*"})
 with urllib.request.urlopen(req,timeout=45) as r:
  body=r.read()
  if r.headers.get("Content-Encoding")=="gzip":
   import gzip
   body=gzip.decompress(body)
  return body
def listing(text,market):
 rows=list(csv.DictReader(io.StringIO(text),delimiter="|"))
 result=[]
 for row in rows:
  symbol=(row.get("Symbol") if market=="NASDAQ" else row.get("ACT Symbol")) or ""
  symbol=symbol.strip()
  if not symbol or symbol.startswith("File Creation Time") or row.get("Test Issue","N")=="Y":continue
  result.append((market,symbol,(row.get("Security Name") or "").strip(),(row.get("ETF") or "").strip(),(row.get("Exchange") or market).strip()))
 return result
def main():
 agent=os.getenv("SEC_USER_AGENT","")
 if "@" not in agent:raise SystemExit("SEC_USER_AGENT secret required")
 root=Path("state");root.mkdir(exist_ok=True)
 dbfile=root/"marketwide.sqlite"
 # Existing state is mandatory after initial bootstrap. Fail closed if recovery is missing.
 if (root/"marketwide_initialized").exists() and not dbfile.exists():raise SystemExit("CONTINUITY_BLOCKED: database missing")
 db=sqlite3.connect(dbfile)
 db.executescript("""
 CREATE TABLE IF NOT EXISTS securities(market TEXT,symbol TEXT,name TEXT,etf TEXT,venue TEXT,first_seen TEXT,last_seen TEXT,PRIMARY KEY(market,symbol));
 CREATE TABLE IF NOT EXISTS sec_filings(cik TEXT,accession_path TEXT,form TEXT,filing_date TEXT,first_seen TEXT,PRIMARY KEY(cik,accession_path));
 CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY,started TEXT,finished TEXT,census INTEGER,sec_records INTEGER,new_filings INTEGER,coverage_status TEXT,receipt TEXT);
 CREATE TRIGGER IF NOT EXISTS runs_immutable_update BEFORE UPDATE ON runs BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS runs_immutable_delete BEFORE DELETE ON runs BEGIN SELECT RAISE(ABORT,'immutable');END;
 CREATE TRIGGER IF NOT EXISTS sec_filings_immutable_delete BEFORE DELETE ON sec_filings BEGIN SELECT RAISE(ABORT,'immutable');END;
 """)
 rid=dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ");started=now()
 feeds={"nasdaq":"https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt","other":"https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"}
 observations={}
 records=[]
 for key,url in feeds.items():
  try:
   body=get(url,agent);items=listing(body.decode("utf-8-sig",errors="replace"),"NASDAQ" if key=="nasdaq" else "OTHER")
   if not items:raise ValueError("empty directory")
   records+=items;observations[key]={"status":"OK","count":len(items),"url":url,"sha256":hashlib.sha256(body).hexdigest(),"checked_at":now()}
  except Exception as e:observations[key]={"status":"FAILED","error":str(e)[:250],"url":url,"checked_at":now()}
 # Fail closed: no partial census is allowed to replace a full prior census.
 if len(records)==0 or any(v["status"]!="OK" for v in observations.values()):
  print(json.dumps({"run_id":rid,"status":"CENSUS_BLOCKED","feeds":observations},indent=2));sys.exit(2)
 for market,symbol,name,etf,venue in records:
  db.execute("INSERT INTO securities VALUES(?,?,?,?,?,?,?) ON CONFLICT(market,symbol) DO UPDATE SET name=excluded.name,etf=excluded.etf,venue=excluded.venue,last_seen=excluded.last_seen",(market,symbol,name,etf,venue,started,started))
 db.commit()
 # SEC master.idx is refreshed nightly, not continuously. Inspect latest completed business-day indexes.
 # Friday or preceding business days are retried until available; 404s are logged, never counted as coverage.
 today=dt.datetime.now(UTC).date()
 sec_obs=[];new=0;indexed=0
 for offset in range(0,5):
  day=today-dt.timedelta(days=offset)
  if day.weekday()>=5:continue
  q=(day.month-1)//3+1
  url=f"https://www.sec.gov/Archives/edgar/daily-index/{day.year}/QTR{q}/master.{day:%Y%m%d}.idx"
  try:
   body=get(url,agent);txt=body.decode("latin-1")
   if "CIK|Company Name|Form Type|Date Filed|Filename" not in txt:raise ValueError("invalid index header")
   lines=txt.split("-----",1)[-1].splitlines()
   count=0
   for line in lines:
    parts=line.split("|")
    if len(parts)!=5 or not parts[0].strip().isdigit():continue
    cik,_,form,filed,filename=parts
    new+=db.execute("INSERT OR IGNORE INTO sec_filings VALUES(?,?,?,?,?)",(cik.zfill(10),filename,form,filed,now())).rowcount
    count+=1
   indexed+=count
   sec_obs.append({"date":str(day),"status":"OK","records":count,"url":url,"checked_at":now()})
   break
  except Exception as e:sec_obs.append({"date":str(day),"status":"FAILED","error":str(e)[:150],"url":url})
 db.commit()
 census=len(records)
 status="PARTIAL: SEC index not available" if not indexed else "SEC index observed; price/news/ETF holdings unavailable"
 receipt={"run_id":rid,"started":started,"ended":now(),"census_rows":census,"unique_symbols":len(set(s for _,s,*_ in records)),"nasdaq_count":observations["nasdaq"].get("count",0),"other_exchange_count":observations["other"].get("count",0),"etf_flag_yes":sum(1 for x in records if x[3]=="Y"),"feeds":observations,"sec_indexes":sec_obs,"sec_index_records":indexed,"new_sec_filing_records":new,"full_market_hourly_coverage":"BLOCKED: no bulk price, news, and ETF holdings feeds","scope_note":"Listing census, not individual issuer forensic review; SEC index not realtime","status":status}
 db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?)",(rid,started,now(),census,indexed,new,status,json.dumps(receipt,sort_keys=True)));db.commit()
 integrity=db.execute("PRAGMA integrity_check").fetchone()[0]
 if integrity!="ok":raise RuntimeError("SQLite integrity: "+integrity)
 db.close()
 (root/"marketwide_initialized").write_text(rid)
 receipt["db_sha256"]=hashlib.sha256(dbfile.read_bytes()).hexdigest()
 (root/("marketwide_receipt_"+rid+".json")).write_text(json.dumps(receipt,indent=2))
 print(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
