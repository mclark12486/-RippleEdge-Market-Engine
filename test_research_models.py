import unittest
from research_models import reconcile_balance,cash_flow,dcf_scenarios,catalyst_score,fund_gate,forecast_eligibility
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
 def test_forecast(self):
  self.assertEqual(forecast_eligibility({})["status"],"RESEARCH_ONLY")
if __name__=="__main__":unittest.main()
