"""RippleEdge shadow analytical primitives. Not investment recommendations."""
import datetime as dt, math
def reconcile_balance(assets,liabilities,equity,tolerance=0.01):
 if any(v is None or not math.isfinite(float(v)) for v in (assets,liabilities,equity)):return {"status":"INSUFFICIENT_EVIDENCE"}
 gap=float(assets)-float(liabilities)-float(equity)
 return {"status":"PASS" if abs(gap)<=max(1,abs(float(assets))*tolerance) else "FLAG","gap":gap,"relative_gap":gap/max(1,abs(float(assets)))}
def cash_flow(cfo,capex,sbc=None):
 if cfo is None or capex is None:return {"status":"INSUFFICIENT_EVIDENCE"}
 if not all(math.isfinite(float(v)) for v in (cfo,capex)):return {"status":"INVALID"}
 result={"status":"PARTIAL","cfo":float(cfo),"capex":abs(float(capex)),"fcf":float(cfo)-abs(float(capex))}
 if sbc is not None:result["sbc_pct_cfo"]=float(sbc)/float(cfo) if cfo else None
 return result
def dcf_scenarios(fcf,shares,net_debt,assumptions):
 """Explicit conditional scenario math, not an independently verified fair value."""
 if fcf is None or shares is None or net_debt is None or shares<=0:return {"status":"INSUFFICIENT_EVIDENCE"}
 out={}
 for label in ("bear","base","bull"):
  a=assumptions.get(label)
  if not a or not all(k in a for k in ("growth","discount","terminal","years")):continue
  g,r,t,n=(float(a["growth"]),float(a["discount"]),float(a["terminal"]),int(a["years"]))
  if n<1 or n>20 or r<=t or r<=-1 or g<=-1:continue
  pv=sum(float(fcf)*(1+g)**year/(1+r)**year for year in range(1,n+1))
  terminal=float(fcf)*(1+g)**n*(1+t)/(r-t)/(1+r)**n
  equity=pv+terminal-float(net_debt)
  out[label]={"conditional_per_share":equity/float(shares),"enterprise_value":pv+terminal,"assumptions":a}
 return {"status":"SCENARIO_ONLY" if len(out)==3 else "INSUFFICIENT_EVIDENCE","scenarios":out,"warning":"Requires normalized audited FCF, diluted shares, net debt and defensible assumptions; not a price target"}
def catalyst_score(event):
 """Transparent evidence ranking; never predicts that a stock will rise."""
 score=0
 score+= {"primary_fulltext":4,"primary_metadata":2,"secondary":0}.get(event.get("source_class"),0)
 score+=2 if event.get("confirmed") else 0
 score+=2 if event.get("economic_impact_quantified") else 0
 score+=1 if event.get("date_verified") else 0
 score-=2 if event.get("contradiction") else 0
 score-=2 if event.get("already_priced_in") else 0
 return {"score":score,"state":"REVIEW" if score>=6 else "WATCH" if score>=3 else "PASS","predictive":False}
def fund_gate(holdings,nav,expense_ratio,asof):
 if not holdings or nav is None or expense_ratio is None or not asof:return {"status":"INSUFFICIENT_EVIDENCE","missing":"holdings, NAV, expenses or as-of date"}
 weights=[float(h["weight"]) for h in holdings]
 if any(x<0 for x in weights) or sum(weights)>1.02:return {"status":"INVALID_WEIGHTS"}
 return {"status":"PARTIAL","holdings_count":len(weights),"reported_weight_sum":sum(weights),"top10_concentration":sum(sorted(weights,reverse=True)[:10]),"nav":nav,"expense_ratio":expense_ratio,"asof":asof,"warning":"Fund look-through valuation requires dated constituent valuations and full holdings"}
def forecast_eligibility(record):
 required=("frozen_at","evidence_cutoff","direction","entry_band","invalidation","horizon","benchmark","costs","source_receipts")
 missing=[k for k in required if not record.get(k)]
 return {"status":"ELIGIBLE_SHADOW" if not missing else "RESEARCH_ONLY","missing":missing}
