"""Read-only Massive historical entitlement probe; never print API credentials.
Run in Actions with MASSIVE_API_KEY. No historical performance is claimed.
"""
import datetime as dt
import json
import os
from pathlib import Path
import urllib.request
import urllib.error

DATES=("2015-01-05","2020-03-16","2025-12-31")
def probe(fetch):
 out={"status":"UNVERIFIED","checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
      "requested_dates":list(DATES),"checks":[],"all_accessible":False}
 for day in DATES:
  for kind,path in (("grouped_daily",f"/v2/aggs/grouped/locale/us/market/stocks/{day}?adjusted=false"),
                    ("historical_tickers",f"/v3/reference/tickers?market=stocks&date={day}&limit=1")):
   try:
    data=fetch(path)
    status=data.get("status")
    n=len(data.get("results") or [])
    ok=status in ("OK","DELAYED") and n>0
    out["checks"].append({"date":day,"dataset":kind,"accessible":ok,"provider_status":status,"returned_sample_count":n})
   except urllib.error.HTTPError as e:
    out["checks"].append({"date":day,"dataset":kind,"accessible":False,"http_status":e.code,
                          "reason":"NOT_AUTHORIZED_OR_UNAVAILABLE" if e.code in (401,403) else "HTTP_ERROR"})
   except Exception as e:
    out["checks"].append({"date":day,"dataset":kind,"accessible":False,"reason":type(e).__name__})
 out["all_accessible"]=all(x["accessible"] for x in out["checks"])
 out["status"]="SAMPLE_ENDPOINTS_ACCESSIBLE_NOT_DATA_VALIDATED" if out["all_accessible"] else "HISTORICAL_ACCESS_INCOMPLETE"
 out["warning"]="Three date samples do not establish complete history, data licensing, point-in-time security master, dividends or backtest validity."
 return out

def main():
 key=os.getenv("MASSIVE_API_KEY") or os.getenv("POLYGON_API_KEY")
 if not key:
  result={"status":"BLOCKED_NO_API_KEY","checks":[],"all_accessible":False}
 else:
  def fetch(path):
   req=urllib.request.Request("https://api.massive.com"+path,
       headers={"Authorization":"Bearer "+key,"User-Agent":"RippleEdge Omega historical entitlement audit"})
   with urllib.request.urlopen(req,timeout=40) as response:return json.load(response)
  result=probe(fetch)
 Path("state").mkdir(exist_ok=True)
 Path("state/omega_entitlement_receipt.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__":main()
