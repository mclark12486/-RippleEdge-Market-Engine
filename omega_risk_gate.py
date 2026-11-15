"""Omega risk gate for hypothetical/shadow signals, not a live trading service.

Fail closed: missing inputs -> no trade. A stop is not a guaranteed fill.
"""
import math
def decide(signal,portfolio,limits=None):
 limits={"max_position_fraction":0.05,"max_sector_fraction":0.20,
  "max_daily_loss_fraction":0.01,"max_drawdown_fraction":0.08,
  "min_reward_risk":2.0,"max_spread_bps":30,
  "max_data_age_minutes":15,**(limits or {})}
 required=("expected_upside_fraction","estimated_downside_fraction","spread_bps",
           "data_age_minutes","evidence_verified","symbol","sector")
 prequired=("daily_pnl_fraction","drawdown_fraction","sector_exposure_fraction",
            "position_exposure_fraction")
 if any(k not in signal for k in required) or any(k not in portfolio for k in prequired):
  return {"action":"PASS","reason":"MISSING_REQUIRED_EVIDENCE"}
 try:
  u=float(signal["expected_upside_fraction"]);d=float(signal["estimated_downside_fraction"])
  spread=float(signal["spread_bps"]);age=float(signal["data_age_minutes"])
  day=float(portfolio["daily_pnl_fraction"]);dd=float(portfolio["drawdown_fraction"])
  sector=float(portfolio["sector_exposure_fraction"]);pos=float(portfolio["position_exposure_fraction"])
  if not all(math.isfinite(x) for x in (u,d,spread,age,day,dd,sector,pos)):raise ValueError()
 except (ValueError,TypeError):
  return {"action":"PASS","reason":"INVALID_NUMERIC_EVIDENCE"}
 if signal["evidence_verified"] is not True:return {"action":"PASS","reason":"UNVERIFIED_EVIDENCE"}
 if day<=-limits["max_daily_loss_fraction"] or dd>=limits["max_drawdown_fraction"]:
  return {"action":"HALT_NEW_ENTRIES","reason":"PORTFOLIO_RISK_LIMIT"}
 if u<=0 or d<=0 or u/d<limits["min_reward_risk"]:
  return {"action":"PASS","reason":"INSUFFICIENT_REWARD_RISK"}
 if spread>limits["max_spread_bps"] or age>limits["max_data_age_minutes"] or spread<0 or age<0:
  return {"action":"PASS","reason":"STALE_OR_ILLIQUID"}
 if sector>=limits["max_sector_fraction"] or pos>=limits["max_position_fraction"]:
  return {"action":"PASS","reason":"CONCENTRATION_LIMIT"}
 allocation=min(limits["max_position_fraction"]-pos,
                limits["max_sector_fraction"]-sector)
 if allocation<=0:return {"action":"PASS","reason":"NO_CAPACITY"}
 return {"action":"SHADOW_CANDIDATE","max_additional_portfolio_fraction":round(allocation,6),
         "reason":"GATES_PASSED_NOT_PROFIT_GUARANTEED",
         "warning":"Not an execution instruction; losses, slippage and overnight gaps remain possible."}
