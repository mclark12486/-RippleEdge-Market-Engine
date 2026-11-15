"""Omega portfolio replay: fixed weights, next-session entries, cash, benchmark comparison.
Research simulation only. Requires independently authenticated point-in-time bars.
"""
import math
from datetime import datetime,timezone

def _time(s):
 t=datetime.fromisoformat(s.replace("Z","+00:00"))
 if t.tzinfo is None:raise ValueError("timezone required")
 return t.astimezone(timezone.utc)

def evaluate(decision, bars, *, capital=10000, cost_bps=20, max_positions=10):
 if not isinstance(capital,(int,float)) or not math.isfinite(capital) or capital<=0:raise ValueError("invalid capital")
 if not isinstance(cost_bps,(int,float)) or not math.isfinite(cost_bps) or cost_bps<0:raise ValueError("invalid cost")
 if not isinstance(max_positions,int) or max_positions<1:raise ValueError("invalid position cap")
 picks=decision["selected_symbols"]
 if len(picks)!=len(set(picks)) or len(picks)>max_positions:raise ValueError("invalid selection")
 cutoff=_time(decision["decision_at"])
 by_symbol={}
 for b in bars:
  if not all(k in b for k in ("symbol","session_open_at","session_close_at","open","close")):raise ValueError("incomplete bar")
  opened=_time(b["session_open_at"]);closed=_time(b["session_close_at"])
  if opened<=cutoff or closed<=opened:continue
  by_symbol.setdefault(b["symbol"],[]).append((opened,b))
 for rows in by_symbol.values():rows.sort(key=lambda z:z[0])
 symbols=list(picks)+["SPY","VOO"]
 if any(len(by_symbol.get(s,[]))<2 for s in symbols):
  return {"status":"BLOCKED_MISSING_BARS","missing":[s for s in symbols if len(by_symbol.get(s,[]))<2]}
 # Require same entry and exit timestamps for all instruments, preventing
 # favorable date selection or mismatched benchmark windows.
 times={(by_symbol[s][0][1]["session_open_at"],by_symbol[s][1][1]["session_close_at"]) for s in symbols}
 if len(times)!=1:return {"status":"BLOCKED_UNALIGNED_SESSIONS"}
 returns={}
 for s in symbols:
  a=by_symbol[s][0][1];z=by_symbol[s][1][1]
  entry=float(a["open"]);exit_=float(z["close"])
  if not all(math.isfinite(v) and v>0 for v in (entry,exit_)):raise ValueError("invalid bar prices")
  returns[s]=exit_/entry-1
 weight=1/max_positions
 invested=weight*len(picks)
 # Charge round-trip bps on allocated capital, including commissions/slippage assumption.
 gross=sum(weight*returns[s] for s in picks)
 net=gross-invested*cost_bps/10000
 spy=returns["SPY"];voo=returns["VOO"]
 return {"status":"ILLUSTRATIVE_NOT_EXECUTED","decision_sha256":decision["sha256"],
         "capital":capital,"positions":len(picks),"cash_weight":1-invested,
         "position_weight":weight,"round_trip_cost_bps":cost_bps,
         "gross_return":gross,"net_return":net,"ending_equity":capital*(1+net),
         "spy_return":spy,"voo_return":voo,
         "excess_vs_spy":net-spy,"excess_vs_voo":net-voo,
         "beat_both":net>spy and net>voo,
         "entry_session":next(iter(times))[0],"exit_session":next(iter(times))[1],
         "limitations":"No dividends, corporate actions, delisting returns, spreads, intraday liquidity, or independently validated point-in-time universe. Not valid as historical alpha evidence."}
