"""Free research-only historical benchmark trial, 2015-2025.

Yahoo Finance/yfinance is intended for personal research; do not redistribute raw
data. This is a BENCHMARK ONLY trial, not a RippleEdge strategy backtest.
"""
import datetime as dt,hashlib,json,math
from pathlib import Path
SYMBOLS={"SPY":"SPY","VOO":"VOO","QQQ":"QQQ","BERKSHIRE":"BRK-B"}
START="2015-01-01";END_EXCLUSIVE="2026-01-01"
def evaluate(series):
 result={"status":"BENCHMARK_ONLY_UNVALIDATED","period":["2015-01-01","2025-12-31"],
  "rippleedge_return":None,"data_source":"Yahoo Finance via yfinance",
  "comparison":{},"limitations":["Not a RippleEdge strategy backtest",
  "No delisted historical security universe or point-in-time fundamentals",
  "Adjusted closes are indicative total-return proxies; independently verify dividend and split methodology",
  "No transaction costs, taxes or portfolio replication"]}
 for name,rows in series.items():
  vals=[(str(d),float(v)) for d,v in rows if START<=str(d)<END_EXCLUSIVE]
  if len(vals)<2000 or vals[0][0]>"2015-01-09" or vals[-1][0]<"2025-12-24":
   result["comparison"][name]={"status":"INSUFFICIENT_COVERAGE","sessions":len(vals)}
   continue
  if any(not math.isfinite(v) or v<=0 for _,v in vals):raise ValueError("Invalid adjusted close")
  growth=vals[-1][1]/vals[0][1]
  years=(dt.date.fromisoformat(vals[-1][0])-dt.date.fromisoformat(vals[0][0])).days/365.25
  result["comparison"][name]={"status":"EXPLORATORY","first_session":vals[0][0],
   "last_session":vals[-1][0],"sessions":len(vals),
   "growth_multiple":round(growth,6),"cagr_percent":round(100*(growth**(1/years)-1),4),
   "total_return_percent":round(100*(growth-1),4)}
 return result
def main():
 import yfinance as yf
 series={};errors={}
 for name,ticker in SYMBOLS.items():
  try:
   frame=yf.download(ticker,start=START,end=END_EXCLUSIVE,auto_adjust=True,
                     progress=False,threads=False,timeout=30)
   if frame is None or frame.empty:raise ValueError("EMPTY_HISTORY")
   col=frame["Close"]
   if hasattr(col,"columns"):col=col.iloc[:,0]
   series[name]=[(idx.date().isoformat(),value) for idx,value in col.dropna().items()]
  except Exception as exc:
   errors[name]=type(exc).__name__;series[name]=[]
 result=evaluate(series)
 result["download_errors"]=errors
 result["status"]="BENCHMARK_ONLY_PRELIMINARY" if all(
  x["status"]=="EXPLORATORY" for x in result["comparison"].values()) else "BLOCKED_INCOMPLETE_BENCHMARKS"
 Path("state").mkdir(exist_ok=True)
 Path("state/omega_free_benchmarks_2015_2025.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__":main()
