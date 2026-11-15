"""Free 2015-2025 *illustrative* price-only momentum walk-forward pilot.

Fixed present-day candidate basket = survivorship bias; never report as validated
RippleEdge alpha. No broker orders. Real daily bars from Yahoo for research.
"""
import datetime as dt,json,math
from pathlib import Path
from omega_walkforward import compare
SYMBOLS=("SPY","VOO","QQQ","BRK-B","XLF","XLV","XLE","XLI","GLD","TLT")
def fetch_bars():
 import yfinance as yf
 bars={}
 for ticker in SYMBOLS:
  frame=yf.download(ticker,start="2015-01-01",end="2026-01-01",
                    auto_adjust=True,progress=False,threads=False,timeout=40)
  if frame is None or frame.empty:raise ValueError("EMPTY_HISTORY:"+ticker)
  op=frame["Open"];cl=frame["Close"]
  if hasattr(op,"columns"):op=op.iloc[:,0]
  if hasattr(cl,"columns"):cl=cl.iloc[:,0]
  bars[ticker]=[(date.date().isoformat(),float(op.loc[date]),float(cl.loc[date]))
                for date in frame.index]
 return bars
def run(bars):
 dates=[row[0] for row in bars["SPY"]]
 if len(dates)<2500 or dates[0]>"2015-01-09" or dates[-1]<"2025-12-24":
  raise ValueError("INSUFFICIENT_2015_2025_COVERAGE")
 if any([row[0] for row in bars[s]]!=dates for s in SYMBOLS):
  raise ValueError("MISSING_OR_UNALIGNED_SESSIONS_FAIL_CLOSED")
 r=compare(bars,lookback=21,hold=20,cost_bps=20)
 trades=r["trades"]
 if not trades:raise ValueError("NO_TRADES")
 wealth=1.;peak=1.;max_dd=0;losses=0
 for t in trades:
  wealth*=1+t["net_return"];peak=max(peak,wealth)
  max_dd=max(max_dd,1-wealth/peak)
  losses+=t["net_return"]<0
 first=dt.date.fromisoformat(trades[0]["entry_session"])
 last=dt.date.fromisoformat(trades[-1]["exit_session"])
 years=(last-first).days/365.25
 return {"status":"ILLUSTRATIVE_SURVIVORSHIP_BIASED_NOT_VALIDATED",
   "strategy":"21-session relative momentum, one candidate at a time, 20-session rebalance",
   "universe":list(SYMBOLS),"period":["2015-01-01","2025-12-31"],
   "first_entry":str(first),"last_exit":str(last),"trades":len(trades),
   "losing_trade_count":losses,"losing_trade_fraction":round(losses/len(trades),6),
   "max_rebalance_drawdown_fraction":round(max_dd,6),
   "strategy_compounded_fraction":round(r["strategy_compounded"],6),
   "spy_same_window_fraction":round(r["spy_compounded"],6),
   "voo_same_window_fraction":round(r["voo_compounded"],6),
   "strategy_cagr_fraction":round(wealth**(1/years)-1,6),
   "assumed_cost_bps_per_trade":20,
   "rippleedge_production_return":None,
   "limitations":["Present-day selected symbols: survivorship and selection bias",
   "This is an illustrative fixed-rule strategy, NOT historical RippleEdge predictions",
   "Adjusted OHLC may not reproduce actual executable fills",
   "No point-in-time corporate/fundamental data, delisted security universe or market impact",
   "Rebalance drawdown understates intraperiod and intraday drawdowns",
   "No proof of outperformance; future returns unknown"]}
def main():
 try:r=run(fetch_bars())
 except Exception as e:r={"status":"BLOCKED_FREE_DATA", "error_type":type(e).__name__,
                         "error":str(e)[:250],"rippleedge_production_return":None}
 Path("state").mkdir(exist_ok=True)
 Path("state/omega_free_strategy_pilot.json").write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
 print(json.dumps(r,indent=2,sort_keys=True))
if __name__=="__main__":main()
