"""Portfolio drawdown triage for shadow decisions; no live execution.

A risk trigger is a REQUEST FOR REVIEW/DE-RISK, not a guaranteed exit.
Normal stock volatility is separated from portfolio-wide drawdown.
"""
import math
def triage(snapshot):
 required=("portfolio_day_return","portfolio_peak_drawdown","market_day_return",
           "thesis_broken","price_data_fresh","exposure_fraction","estimated_gap_risk")
 if any(k not in snapshot for k in required):
  return {"action":"FREEZE_NEW_RISK","reason":"MISSING_DATA"}
 try:
  day=float(snapshot["portfolio_day_return"]);dd=float(snapshot["portfolio_peak_drawdown"])
  market=float(snapshot["market_day_return"]);exposure=float(snapshot["exposure_fraction"])
  gap=float(snapshot["estimated_gap_risk"])
  if not all(math.isfinite(v) for v in (day,dd,market,exposure,gap)) or not 0<=exposure<=1 or gap<0:
   raise ValueError()
 except (ValueError,TypeError):
  return {"action":"FREEZE_NEW_RISK","reason":"INVALID_DATA"}
 if snapshot["price_data_fresh"] is not True:
  return {"action":"FREEZE_NEW_RISK","reason":"STALE_PRICES"}
 if day<=-.03:
  return {"action":"EMERGENCY_REVIEW","reason":"THREE_PERCENT_PORTFOLIO_LOSS_BREACH",
   "new_entries":False,"suggested_response":"Assess liquidity and reduce correlated exposure where feasible; no guaranteed fills"}
 if day<=-.015 or dd>=.05:
  return {"action":"DE_RISK_REVIEW","reason":"LOSS_OR_DRAWDOWN_WARNING",
   "new_entries":False,"suggested_response":"Review exposures and market regime; avoid reflexively liquidating healthy positions"}
 if snapshot["thesis_broken"] is True:
  return {"action":"THESIS_EXIT_REVIEW","reason":"INVESTMENT_THESIS_INVALIDATED",
   "new_entries":False}
 if market<=-.02 and exposure>.5:
  return {"action":"HEDGE_OR_CASH_REVIEW","reason":"MARKET_STRESS_HIGH_EXPOSURE",
   "new_entries":False}
 if gap>=.03 and exposure>.5:
  return {"action":"REDUCE_OVERNIGHT_RISK_REVIEW","reason":"ESTIMATED_GAP_RISK",
   "new_entries":False}
 return {"action":"HOLD_OR_RESEARCH","reason":"NO_PORTFOLIO_TRIGGER",
  "new_entries":True,"warning":"No guarantee against future losses; risk signals require actual execution and monitoring"}
