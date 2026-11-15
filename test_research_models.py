import unittest
from research_models import reconcile_balance,cash_flow,dcf_scenarios,catalyst_score,fund_gate,forecast_eligibility,valuation_evidence_gate,period_consistency
class ResearchModelsTests(unittest.TestCase):
 def test_balance(self):
  self.assertEqual(reconcile_balance(100,60,40)["status"],"PASS")
  self.assertEqual(reconcile_balance(100,60,20)["status"],"FLAG")
 def test_fcf(self):
  self.assertEqual(cash_flow(120,30)["fcf"],90)
  self.assertEqual(cash_flow(None,30)["status"],"INSUFFICIENT_EVIDENCE")
 def test_dcf(self):
  a={k:{"growth":g,"discount":.12,"terminal":.02,"years":5} for k,g in (("bear",-.02),("base",.03),("bull",.08))}
  x=dcf_scenarios(100,10,200,a)
  self.assertEqual(x["status"],"SCENARIO_ONLY")
  self.assertLess(x["scenarios"]["bear"]["conditional_per_share"],x["scenarios"]["bull"]["conditional_per_share"])
  self.assertEqual(dcf_scenarios(100,0,200,a)["status"],"INSUFFICIENT_EVIDENCE")
 def test_event(self):
  self.assertEqual(catalyst_score({"source_class":"secondary"})["state"],"PASS")
 def test_fund(self):
  self.assertEqual(fund_gate([],None,None,None)["status"],"INSUFFICIENT_EVIDENCE")
 def test_valuation_gate(self):
  self.assertEqual(valuation_evidence_gate({})["status"],"BLOCKED_MISSING_EVIDENCE")
  facts={k:"source" for k in ("cash_flow_source","cash_flow_period","maintenance_capex_source","diluted_shares_source","diluted_shares_asof","cash_source","debt_source","assumption_rationale","filing_accession")}
  facts.update(normalized_fcf=100,diluted_shares=10,cash=20,debt=50,discount_rate=.11,terminal_growth=.02)
  self.assertEqual(valuation_evidence_gate(facts)["status"],"EVIDENCE_READY_FOR_REVIEW")
  facts["discount_rate"]=.01
  self.assertEqual(valuation_evidence_gate(facts)["status"],"BLOCKED_MISSING_EVIDENCE")
 def test_period_conflict(self):
  a={"fiscal_year":2025,"period_end":"2025-12-31","filed":"2026-02-01","value":100}
  b=dict(a,value=105,filed="2026-04-01")
  self.assertEqual(period_consistency([a,b])["status"],"REVIEW_REQUIRED")
 def test_forecast(self):
  self.assertEqual(forecast_eligibility({})["status"],"RESEARCH_ONLY")
if __name__=="__main__":unittest.main()
