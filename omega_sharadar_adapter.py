"""Convert licensed Sharadar SEP/SFP CSV export into Omega historical importer schema.

Preserves permanent dataset ticker identifiers. This does not validate PIT
fundamentals, delisting returns, corporate actions, or historical completeness.
"""
import argparse,csv,hashlib,json
from pathlib import Path
from omega_historical_import import import_csv,FIELDS
def convert(source_csv,destination_csv):
 raw=Path(source_csv).read_bytes();digest=hashlib.sha256(raw).hexdigest()
 n=0
 with Path(source_csv).open(newline="") as inp,Path(destination_csv).open("w",newline="") as out:
  reader=csv.DictReader(inp)
  required=("ticker","date","open","high","low","close","volume")
  if not reader.fieldnames or any(k not in reader.fieldnames for k in required):
   raise ValueError("Sharadar SEP/SFP columns missing")
  writer=csv.DictWriter(out,fieldnames=FIELDS);writer.writeheader()
  for row in reader:
   if "2015-01-01"<=row["date"]<="2025-12-31":
    writer.writerow({"session":row["date"],"symbol":row["ticker"],
      "open":row["open"],"high":row["high"],"low":row["low"],
      "close":row["close"],"volume":row["volume"],
      "source_id":"sharadar-export:"+digest[:16]})
    n+=1
 return {"status":"CONVERTED_UNVALIDATED","rows":n,"source_sha256":digest}
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--input",required=True);ap.add_argument("--converted",required=True)
 ap.add_argument("--db",default="state/omega_historical.sqlite")
 ap.add_argument("--source-license-id",required=True)
 args=ap.parse_args()
 conversion=convert(args.input,args.converted)
 if conversion["rows"]==0:raise SystemExit("BLOCKED: no rows in 2015-2025")
 result=import_csv(args.converted,args.db,args.source_license_id)
 print(json.dumps({"conversion":conversion,"import":result},indent=2))
if __name__=="__main__":main()
