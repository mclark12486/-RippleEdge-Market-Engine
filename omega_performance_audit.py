"""Audit simulated portfolio equity curves against aligned benchmark equity curves."""
import math
def metrics(curve):
 if len(curve)<3:raise ValueError("insufficient observations")
 vals=[float(v) for v in curve]
 if any(not math.isfinite(v) or v<=0 for v in vals):raise ValueError("invalid equity")
 returns=[vals[i]/vals[i-1]-1 for i in range(1,len(vals))]
 peak=vals[0];dd=0
 for v in vals:
  peak=max(peak,v);dd=max(dd,1-v/peak)
 mean=sum(returns)/len(returns)
 var=sum((x-mean)**2 for x in returns)/len(returns)
 return {"total_return":vals[-1]/vals[0]-1,"max_drawdown":dd,
  "worst_session_return":min(returns),"losing_sessions":sum(x<0 for x in returns),
  "observed_sessions":len(returns),
  "annualized_volatility":math.sqrt(var*252),
  "sharpe_zero_riskfree":mean/math.sqrt(var)*math.sqrt(252) if var>0 else None}
def compare(strategy,benchmarks):
 out={"strategy":metrics(strategy),"benchmarks":{},"status":"EXPLORATORY_ALIGNED"}
 for name,curve in benchmarks.items():
  if len(curve)!=len(strategy):raise ValueError("benchmark sessions unaligned")
  out["benchmarks"][name]=metrics(curve)
 return out
