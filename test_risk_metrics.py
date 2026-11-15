import unittest
from risk_metrics import trade_risk

class RiskMetricsTests(unittest.TestCase):
 def test_empty_is_unproven(self):
  x=trade_risk([])
  self.assertEqual(x["sample_size"],0)
  self.assertIsNone(x["portfolio_max_drawdown"])
  self.assertIsNone(x["portfolio_annualized_volatility"])
 def test_negative_outcomes_and_both_benchmarks(self):
  data=[{"net_return":-.1,"excess_return":-.08,"excess_vs_spy":-.08,"excess_vs_voo":-.09,"benchmark_return":-.02},
        {"net_return":.06,"excess_return":.05,"excess_vs_spy":.05,"excess_vs_voo":.04,"benchmark_return":.01}]
  x=trade_risk(data)
  self.assertEqual(x["worst_trade_return"],-.1)
  self.assertEqual(x["beat_both_fraction"],.5)
  self.assertEqual(x["five_session_spy_environments"]["spy_down_5_sessions"]["count"],1)
  self.assertEqual(x["five_session_spy_environments"]["spy_flat_or_up_5_sessions"]["count"],1)
  self.assertIsNone(x["portfolio_max_drawdown"])
if __name__=="__main__":unittest.main()
