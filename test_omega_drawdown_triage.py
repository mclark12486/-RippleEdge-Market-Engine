import unittest
from omega_drawdown_triage import triage
BASE={"portfolio_day_return":-.004,"portfolio_peak_drawdown":.01,
      "market_day_return":-.003,"thesis_broken":False,"price_data_fresh":True,
      "exposure_fraction":.6,"estimated_gap_risk":.01}
class DrawdownTests(unittest.TestCase):
 def test_small_red_not_forced_sale(self):self.assertEqual(triage(BASE)["action"],"HOLD_OR_RESEARCH")
 def test_three_percent_emergency(self):self.assertEqual(triage({**BASE,"portfolio_day_return":-.05})["action"],"EMERGENCY_REVIEW")
 def test_early_warning(self):self.assertEqual(triage({**BASE,"portfolio_day_return":-.02})["action"],"DE_RISK_REVIEW")
 def test_thesis_break(self):self.assertEqual(triage({**BASE,"thesis_broken":True})["action"],"THESIS_EXIT_REVIEW")
 def test_market_stress(self):self.assertEqual(triage({**BASE,"market_day_return":-.03})["action"],"HEDGE_OR_CASH_REVIEW")
 def test_stale_freezes(self):self.assertEqual(triage({**BASE,"price_data_fresh":False})["action"],"FREEZE_NEW_RISK")
 def test_missing_freezes(self):self.assertEqual(triage({})["action"],"FREEZE_NEW_RISK")
if __name__=="__main__":unittest.main()
