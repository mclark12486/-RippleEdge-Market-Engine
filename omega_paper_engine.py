"""RippleEdge Omega: independent, deterministic paper portfolio.

No real accounts, broker API, live execution or claimed alpha. Each session
requires externally supplied, point-in-time prices and frozen signals.
"""
import hashlib,json,math
from omega_drawdown_triage import triage
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,allow_nan=False).encode()).hexdigest()
def initial(cash=10000):
 if not math.isfinite(float(cash)) or cash<=0:raise ValueError("cash")
 return {"cash":float(cash),"positions":{},"equity":float(cash),"peak":float(cash),
         "previous_equity":float(cash),"last_session":None,"ledger":[]}
def step(state,session,prices,signals,market_return=0,cost_bps=20):
 """Close-to-close paper rebalance; signals MUST be frozen before this session.
 Positions execute at current observed close plus cost: optimistic simulation,
 not executable fills. No leverage/shorts. Independent defense can veto alpha.
 """
 s=json.loads(json.dumps(state))
 if s["last_session"] is not None and session<=s["last_session"]:raise ValueError("nonmonotonic session")
 if not isinstance(prices,dict) or not prices:raise ValueError("prices")
 if not 0<=cost_bps<=1000:raise ValueError("cost")
 for sym,qty in s["positions"].items():
  if sym not in prices:raise ValueError("missing price for held symbol "+sym)
 for sym,price in prices.items():
  if not math.isfinite(float(price)) or float(price)<=0:raise ValueError("bad price")
 if not math.isfinite(float(market_return)):raise ValueError("market")
 start_eq=s["cash"]+sum(qty*float(prices[sym]) for sym,qty in s["positions"].items())
 if start_eq<=0:raise ValueError("equity")
 day=start_eq/s["previous_equity"]-1
 peak=max(s["peak"],start_eq)
 exposure=sum(qty*float(prices[sym]) for sym,qty in s["positions"].items())/start_eq
 risk=triage({"portfolio_day_return":day,"portfolio_peak_drawdown":1-start_eq/peak,
  "market_day_return":market_return,"thesis_broken":any(x.get("thesis_broken") is True for x in signals),
  "price_data_fresh":True,"exposure_fraction":min(1,exposure),"estimated_gap_risk":0})
 orders=[]
 def sell(sym,reason):
  qty=s["positions"].pop(sym,0)
  if qty:
   gross=qty*float(prices[sym]);fee=gross*cost_bps/10000
   s["cash"]+=gross-fee
   orders.append({"symbol":sym,"side":"SELL","quantity":qty,"fee":round(fee,6),"reason":reason})
 # Independently de-risk on portfolio triggers; no same-session loss erasure.
 if risk["action"] in ("EMERGENCY_REVIEW","DE_RISK_REVIEW","HEDGE_OR_CASH_REVIEW"):
  for sym in list(s["positions"]):sell(sym,risk["action"])
 else:
  for x in signals:
   if x.get("thesis_broken") is True and x.get("symbol") in s["positions"]:
    sell(x["symbol"],"THESIS_INVALIDATED")
 # Only accept pre-session signals, max 5% per new position, 20% gross exposure.
 if risk["action"]=="HOLD_OR_RESEARCH":
  for x in sorted(signals,key=lambda a:(-float(a.get("score",0)),str(a.get("symbol","")))):
   sym=x.get("symbol")
   if sym not in prices or sym in s["positions"]:continue
   if x.get("evidence_verified") is not True or x.get("frozen_before_session") is not True:continue
   if x.get("thesis_broken") is True:continue
   try:
    upside=float(x["upside"]);downside=float(x["downside"])
    if not all(math.isfinite(v) for v in (upside,downside)) or downside<=0 or upside/downside<2:continue
   except (ValueError,TypeError,KeyError):continue
   invested=sum(q*float(prices[t]) for t,q in s["positions"].items())
   target=min(start_eq*.05,max(0,start_eq*.20-invested),s["cash"])
   price=float(prices[sym]);qty=int(target/(price*(1+cost_bps/10000)))
   if qty<1:continue
   gross=qty*price;fee=gross*cost_bps/10000
   s["cash"]-=gross+fee;s["positions"][sym]=qty
   orders.append({"symbol":sym,"side":"BUY","quantity":qty,"fee":round(fee,6),"reason":"VERIFIED_ALPHA_SIGNAL"})
 s["equity"]=s["cash"]+sum(q*float(prices[t]) for t,q in s["positions"].items())
 s["peak"]=max(peak,s["equity"]);s["previous_equity"]=s["equity"];s["last_session"]=session
 receipt={"session":session,"equity":round(s["equity"],6),"day_return":round(day,6),
          "risk":risk["action"],"paper_orders":orders,"cash":round(s["cash"],6),
          "execution":"SIMULATED_CLOSE_ONLY_NOT_LIVE"}
 receipt["sha256"]=digest(receipt);s["ledger"].append(receipt)
 return s
