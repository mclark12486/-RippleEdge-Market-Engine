"""Import licensed historical OHLCV CSV into isolated Omega database.

Input contract: session,symbol,open,high,low,close,volume,source_id
Requires a separate provenance manifest; NEVER asserts total-return or PIT validity.
No current ticker census filter: preserve delisted historical symbols.
"""
import argparse,csv,datetime as dt,hashlib,json,math,sqlite3
from pathlib import Path
FIELDS=("session","symbol","open","high","low","close","volume","source_id")
def import_csv(csv_path,db_path,source):
 if not source or not source.strip():raise ValueError("Source/license identifier required")
 raw=Path(csv_path).read_bytes()
 digest=hashlib.sha256(raw).hexdigest()
 records=[];seen=set()
 with Path(csv_path).open(newline="") as fh:
  reader=csv.DictReader(fh)
  if not reader.fieldnames or any(f not in reader.fieldnames for f in FIELDS):
   raise ValueError("Missing required CSV columns")
  for row in reader:
   day=dt.date.fromisoformat(row["session"])
   if not dt.date(2015,1,1)<=day<=dt.date(2025,12,31):raise ValueError("Outside historical window")
   symbol=row["symbol"].strip()
   if not symbol or not row["source_id"].strip():raise ValueError("Missing symbol or row provenance")
   key=(str(day),symbol)
   if key in seen:raise ValueError("Duplicate symbol-session")
   seen.add(key)
   o,h,l,c,v=(float(row[k]) for k in ("open","high","low","close","volume"))
   if not all(map(math.isfinite,(o,h,l,c,v))) or min(o,h,l,c)<=0 or v<0 or h<max(o,c,l) or l>min(o,c,h):
    raise ValueError("Invalid OHLCV")
   records.append((str(day),symbol,o,h,l,c,v,row["source_id"].strip(),digest))
 if not records:raise ValueError("Empty input")
 db=Path(db_path);db.parent.mkdir(parents=True,exist_ok=True)
 with sqlite3.connect(db) as conn:
  conn.execute("CREATE TABLE IF NOT EXISTS historical_bars(session TEXT NOT NULL,symbol TEXT NOT NULL,open REAL,high REAL,low REAL,close REAL,volume REAL,source_id TEXT NOT NULL,file_sha256 TEXT NOT NULL,PRIMARY KEY(session,symbol))")
  # Reject collisions instead of silently overwriting earlier evidence.
  conn.executemany("INSERT INTO historical_bars VALUES(?,?,?,?,?,?,?,?,?)",records)
  count=conn.execute("SELECT COUNT(*) FROM historical_bars").fetchone()[0]
 return {"status":"IMPORTED_UNVALIDATED","source":source,"file_sha256":digest,
         "rows_imported":len(records),"total_rows":count,
         "earliest_session":min(r[0] for r in records),"latest_session":max(r[0] for r in records),
         "warning":"Historical bars alone cannot validate universe, dividends, delistings, or point-in-time features."}
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--csv",required=True);ap.add_argument("--db",default="state/omega_historical.sqlite")
 ap.add_argument("--source",required=True);ap.add_argument("--receipt",default="state/omega_historical_import_receipt.json")
 args=ap.parse_args()
 receipt=import_csv(args.csv,args.db,args.source)
 Path(args.receipt).parent.mkdir(parents=True,exist_ok=True)
 Path(args.receipt).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
 print(json.dumps(receipt,indent=2,sort_keys=True))
if __name__=="__main__":main()
