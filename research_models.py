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

def valuation_evidence_gate(facts):
 """Prevent illustrative DCFs from being advertised as independently verified equity fair values."""
 required=("cash_flow_source","cash_flow_period","maintenance_capex_source","diluted_shares_source","diluted_shares_asof","cash_source","debt_source","assumption_rationale","filing_accession")
 missing=[k for k in required if not facts.get(k)]
 checks={}
 for k in ("normalized_fcf","diluted_shares","cash","debt","discount_rate","terminal_growth"):
  try:
   v=float(facts[k]);checks[k]=math.isfinite(v)
  except (KeyError,TypeError,ValueError,OverflowError):checks[k]=False
 if checks.get("diluted_shares") and float(facts["diluted_shares"])<=0:checks["diluted_shares"]=False
 if checks.get("discount_rate") and checks.get("terminal_growth") and float(facts["discount_rate"])<=float(facts["terminal_growth"]):checks["discount_rate"]=False
 missing += [k for k,ok in checks.items() if not ok]
 return {"status":"EVIDENCE_READY_FOR_REVIEW" if not missing else "BLOCKED_MISSING_EVIDENCE","missing":sorted(set(missing)),"automatically_verified_fair_value":False}

def period_consistency(observations):
 """Check filing period consistency and point to discrepancies; do not resolve them silently."""
 if not observations:return {"status":"INSUFFICIENT_EVIDENCE","issues":["no observations"]}
 issues=[];seen={}
 for x in observations:
  year=x.get("fiscal_year");period=x.get("period_end");filed=x.get("filed");value=x.get("value")
  if not year or not period or not filed or not isinstance(value,(int,float)) or not math.isfinite(value):
   issues.append({"record":x,"issue":"incomplete or invalid filing observation"});continue
  key=(year,period)
  if key in seen and seen[key]!=value:issues.append({"fiscal_year":year,"period_end":period,"issue":"conflicting reported values; restatement review required"})
  seen[key]=value
 return {"status":"REVIEW_REQUIRED" if issues else "CONSISTENT_OBSERVATIONS","issues":issues}

def score_frozen_forecast(forecast, observations):
 """Score only after a frozen forecast's dated horizon using observed prices.
 No backfill of predictions or invented fills. Prices are supplied with provenance.
 """
 needed=("frozen_at","evidence_cutoff","direction","entry_price","horizon_sessions","benchmark","cost_bps")
 missing=[k for k in needed if forecast.get(k) is None]
 if missing:return {"status":"UNSCORABLE","missing":missing}
 try:
  entry=float(forecast["entry_price"]);n=int(forecast["horizon_sessions"]);cost=float(forecast["cost_bps"])
  if not math.isfinite(entry) or entry<=0 or n<=0 or cost<0 or not math.isfinite(cost):raise ValueError("invalid forecast parameters")
  if forecast["direction"] not in ("LONG","SHORT"):raise ValueError("unsupported direction")
  if forecast["evidence_cutoff"]>forecast["frozen_at"]:raise ValueError("evidence cutoff after forecast freeze")
  eligible=[x for x in observations if x.get("date") and x["date"]>forecast["frozen_at"][:10]]
  eligible.sort(key=lambda x:x["date"])
  if len(eligible)<n:return {"status":"PENDING_HORIZON","observed_sessions":len(eligible),"required_sessions":n}
  point=eligible[n-1]
  exit_price=float(point["close"]);benchmark_return=float(point["benchmark_return"])
  if exit_price<=0 or not math.isfinite(exit_price) or not math.isfinite(benchmark_return) or not point.get("price_source") or not point.get("benchmark_source"):raise ValueError("missing verified exit evidence")
  gross=(exit_price/entry-1)*(1 if forecast["direction"]=="LONG" else -1)
  net=gross-cost/10000
  return {"status":"SCORED","horizon_date":point["date"],"gross_return":gross,"net_return":net,"benchmark_return":benchmark_return,"excess_return":net-benchmark_return,"exit_price":exit_price,"price_source":point["price_source"],"benchmark_source":point["benchmark_source"],"warning":"Requires independent verification of actual tradability, entry fill, corporate actions and borrow costs"}
 except (ValueError,TypeError,OverflowError) as exc:return {"status":"UNSCORABLE","reason":str(exc)}

def verify_catalyst_evidence(event):
 """A filing index hit is not proof of a material catalyst."""
 required=("primary_document_url","document_retrieved_at","document_sha256","source_date","issuer","event_description","quoted_evidence")
 missing=[k for k in required if not event.get(k)]
 if event.get("source_class")!="primary_fulltext":missing.append("primary_fulltext")
 if not event.get("economic_impact_quantified"):missing.append("economic_impact_quantified")
 if not event.get("future_effective_date"):missing.append("future_effective_date")
 if event.get("contradiction"):return {"status":"CONTRADICTED","missing":sorted(set(missing)),"verified_positive_catalyst":False}
 return {"status":"DOCUMENTED_REVIEW_REQUIRED" if not missing else "DISCOVERY_ONLY","missing":sorted(set(missing)),"verified_positive_catalyst":False}
