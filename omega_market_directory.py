"""Build a reproducible U.S. SEC registrant directory, not a claim of full listed-market coverage.

SEC company_tickers.json covers SEC registrants with tickers, including some
non-US and non-common-stock securities. Keep raw CIK and report scope.
"""
import csv,datetime as dt,json,os,urllib.request
from pathlib import Path
URL="https://www.sec.gov/files/company_tickers.json"
def build(raw):
 rows=raw.values() if isinstance(raw,dict) else raw
 out=[];seen=set();bad=0
 for x in rows:
  try:
   ticker=str(x["ticker"]).strip().upper()
   name=str(x["title"]).strip()
   cik=int(x["cik_str"])
   if not ticker or not name or cik<=0 or (ticker,cik) in seen:raise ValueError("invalid")
   seen.add((ticker,cik));out.append({"symbol":ticker,"name":name,"cik":str(cik).zfill(10)})
  except (KeyError,ValueError,TypeError):bad+=1
 out.sort(key=lambda x:(x["symbol"],x["cik"]))
 if not out:raise ValueError("no valid SEC registrants")
 return out,{"source":URL,"retrieved_at":dt.datetime.now(dt.timezone.utc).isoformat(),
  "registrants_with_tickers":len(out),"rejected_records":bad,
  "scope":"SEC tickers; not verified US-listed common-equity universe, not subsidiaries or all securities",
  "marketwide_complete":False}
def fetch():
 agent=os.environ.get("SEC_USER_AGENT","")
 if "@" not in agent:raise ValueError("SEC_USER_AGENT with contact required")
 req=urllib.request.Request(URL,headers={"User-Agent":agent,"Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
def main():
 rows,receipt=build(fetch())
 dest=Path("state/omega_sec_company_directory.csv");dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=["symbol","name","cik"]);w.writeheader();w.writerows(rows)
 Path("state/omega_sec_company_directory_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
 print(json.dumps(receipt))
if __name__=="__main__":main()
