"""Exploratory price-only walk-forward comparison. NOT point-in-time validated.
The input must be authenticated independently before results count as evidence.
"""
import math

def compare(bars, *, lookback=5, hold=5, cost_bps=20):
 """Equal-weight top momentum, no overlap, next-session OPEN to later CLOSE.
 bars: symbol -> sorted (date, open, close) with aligned trading sessions.
 Missing bars block the comparison rather than dropping losing instruments.
 """
 if lookback<2 or hold<1 or cost_bps<0:raise ValueError("invalid parameters")
 if "SPY" not in bars or "VOO" not in bars:raise ValueError("SPY and VOO required")
 dates=[x[0] for x in bars["SPY"]]
 if dates!=[x[0] for x in bars["VOO"]]:raise ValueError("unaligned benchmarks")
 if any(dates[i]>=dates[i+1] for i in range(len(dates)-1)):raise ValueError("nonascending dates")
 for symbol,series in bars.items():
  if len(series)!=len(dates) or [x[0] for x in series]!=dates:raise ValueError("incomplete or unaligned "+symbol)
  if any(not all(math.isfinite(float(v)) and v>0 for v in (o,c)) for _,o,c in series):raise ValueError("invalid prices")
 trades=[]
 for i in range(lookback,len(dates)-hold,hold):
  # Only closes through index i-1 are available when ranking.
  ranked=sorted(((bars[s][i-1][2]/bars[s][i-lookback][2]-1,s)
                 for s in bars if s not in ("SPY","VOO")),reverse=True)
  if not ranked:break
  symbol=ranked[0][1]
  entry=bars[symbol][i][1];exit_=bars[symbol][i+hold][2]
  net=exit_/entry-1-cost_bps/10000
  spy=bars["SPY"][i+hold][2]/bars["SPY"][i][1]-1
  voo=bars["VOO"][i+hold][2]/bars["VOO"][i][1]-1
  trades.append({"decision_session":dates[i-1],"entry_session":dates[i],
   "exit_session":dates[i+hold],"symbol":symbol,"net_return":net,
   "spy_return":spy,"voo_return":voo,"beat_both":net>spy and net>voo})
 def compounded(k):
  result=1.
  for t in trades:result*=1+t[k]
  return result-1
 return {"status":"EXPLORATORY_UNVALIDATED","trades":trades,
  "strategy_compounded":compounded("net_return"),
  "spy_compounded":compounded("spy_return"),
  "voo_compounded":compounded("voo_return"),
  "limitations":"Unverified historical universe, survivorship, dividends, corporate actions, delisting, realistic fills and point-in-time availability. Do not report as proven alpha."}
