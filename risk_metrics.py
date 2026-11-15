"""Evidence-limited risk statistics for independently scored shadow forecasts.
Trade-level dispersion is not portfolio volatility; no portfolio drawdown claim.
"""
import math
import statistics

def trade_risk(outcomes):
 """Only use verified, frozen-forecast outcomes. No synthetic equity curve."""
 n=len(outcomes)
 result={"sample_size":n,"status":"INSUFFICIENT_SAMPLE" if n<30 else "DESCRIPTIVE_ONLY",
         "portfolio_max_drawdown":None,"portfolio_annualized_volatility":None,
         "risk_adjusted_portfolio_alpha":None,
         "reason":"No timestamped investable portfolio equity curve, positions or fills"}
 if not n:return result
 returns=[float(x["net_return"]) for x in outcomes]
 if not all(math.isfinite(x) for x in returns):raise ValueError("nonfinite return")
 result.update(worst_trade_return=min(returns),
  best_trade_return=max(returns),
  trade_win_fraction=sum(x>0 for x in returns)/n,
  mean_trade_return=statistics.mean(returns),
  trade_return_stddev=statistics.stdev(returns) if n>1 else None,
  downside_trade_rms=math.sqrt(sum(min(0,x)**2 for x in returns)/n),
  negative_trade_fraction=sum(x<0 for x in returns)/n)
 dual=[x for x in outcomes if "excess_vs_spy" in x and "excess_vs_voo" in x]
 result["dual_benchmark_sample_size"]=len(dual)
 result["beat_both_fraction"]=sum(x["excess_vs_spy"]>0 and x["excess_vs_voo"]>0 for x in dual)/len(dual) if dual else None
 # Benchmark-return buckets reflect observed five-session environments,
 # not independently established macroeconomic bull/bear regimes.
 regimes={}
 for label,filter_fn in (
  ("spy_down_5_sessions",lambda x:x.get("benchmark_spy_return",x.get("benchmark_return",0))<0),
  ("spy_flat_or_up_5_sessions",lambda x:x.get("benchmark_spy_return",x.get("benchmark_return",0))>=0)):
  subset=[x for x in outcomes if filter_fn(x)]
  regimes[label]={"count":len(subset),
   "mean_net_return":statistics.mean(float(x["net_return"]) for x in subset) if subset else None,
   "mean_excess_vs_spy":statistics.mean(float(x.get("excess_vs_spy",x["excess_return"])) for x in subset) if subset else None,
   "mean_excess_vs_voo":statistics.mean(float(x["excess_vs_voo"]) for x in subset if "excess_vs_voo" in x) if any("excess_vs_voo" in x for x in subset) else None}
 result["five_session_spy_environments"]=regimes
 return result
