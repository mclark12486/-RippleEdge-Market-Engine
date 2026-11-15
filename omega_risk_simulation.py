"""Simulate drawdown triage against chronological portfolio daily returns.

Daily-close monitoring cannot prevent intraday losses or overnight gaps.
Once triggered, next-session cash transition is simulated, not executed.
"""
import math
from omega_drawdown_triage import triage
def simulate(daily_returns,market_returns,*,reset_after=5):
 if len(daily_returns)!=len(market_returns) or len(daily_returns)<2:raise ValueError("aligned daily series required")
 equity=1.;peak=1.;cash_days=0;events=[];curve=[1.]
 for i,(ret,mret) in enumerate(zip(daily_returns,market_returns)):
  ret=float(ret);mret=float(mret)
  if not all(math.isfinite(x) for x in (ret,mret)) or ret<=-1:raise ValueError("invalid return")
  invested=cash_days==0
  equity*=1+ret if invested else 1
  peak=max(peak,equity)
  tri=triage({"portfolio_day_return":ret if invested else 0,
   "portfolio_peak_drawdown":max(0,1-equity/peak),
   "market_day_return":mret,"thesis_broken":False,"price_data_fresh":True,
   "exposure_fraction":1 if invested else 0,"estimated_gap_risk":0})
  if invested and tri["action"] in ("EMERGENCY_REVIEW","DE_RISK_REVIEW"):
   cash_days=reset_after
   events.append({"index":i,"trigger":tri["action"],"effective":"NEXT_SESSION"})
  elif not invested:cash_days-=1
  curve.append(equity)
 return {"status":"ILLUSTRATIVE_DAILY_CLOSE_ONLY","equity_multiple":round(equity,6),
  "max_daily_loss_fraction":round(min(curve[i]/curve[i-1]-1 for i in range(1,len(curve))),6),
  "events":events,"equity_curve":curve,
  "warning":"Uses assumed next-session cash transitions; no fills, transaction costs, intraday data or proof of loss prevention."}
