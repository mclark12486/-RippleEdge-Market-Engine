import unittest
from omega_risk_gate import decide
S={"expected_upside_fraction":.12,"estimated_downside_fraction":.04,
   "spread_bps":10,"data_age_minutes":2,"evidence_verified":True,"symbol":"ABC","sector":"Industrials"}
P={"daily_pnl_fraction":0,"drawdown_fraction":0,"sector_exposure_fraction":.10,"position_exposure_fraction":0}
class RiskTests(unittest.TestCase):
 def test_valid_is_shadow_only(self):self.assertEqual(decide(S,P)["action"],"SHADOW_CANDIDATE")
 def test_no_evidence_fails_closed(self):self.assertEqual(decide({**S,"evidence_verified":False},P)["action"],"PASS")
 def test_missing_fails_closed(self):self.assertEqual(decide({},P)["action"],"PASS")
 def test_daily_loss_halts(self):self.assertEqual(decide(S,{**P,"daily_pnl_fraction":-.02})["action"],"HALT_NEW_ENTRIES")
 def test_drawdown_halts(self):self.assertEqual(decide(S,{**P,"drawdown_fraction":.10})["action"],"HALT_NEW_ENTRIES")
 def test_bad_reward_risk_passes(self):self.assertEqual(decide({**S,"expected_upside_fraction":.02},P)["action"],"PASS")
 def test_stale_passes(self):self.assertEqual(decide({**S,"data_age_minutes":60},P)["action"],"PASS")
 def test_sector_cap_passes(self):self.assertEqual(decide(S,{**P,"sector_exposure_fraction":.25})["action"],"PASS")
if __name__=="__main__":unittest.main()
