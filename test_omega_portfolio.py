import unittest
from omega_replay import freeze_decision
from omega_portfolio import evaluate

def bars(sym,entry,exit_):
 return [{"symbol":sym,"session_open_at":"2020-03-03T14:30:00Z","session_close_at":"2020-03-03T21:00:00Z","open":entry,"close":entry},
         {"symbol":sym,"session_open_at":"2020-03-04T14:30:00Z","session_close_at":"2020-03-04T21:00:00Z","open":exit_,"close":exit_}]
def decision():
 row={"symbol":"A","published_at":"2020-03-02T15:00:00Z","ingested_at":"2020-03-02T15:01:00Z","source_id":"filing","value":1}
 return freeze_decision([row],"2020-03-02T16:00:00Z",lambda r:["A"],"omega-0")
class PortfolioTests(unittest.TestCase):
 def test_cash_cost_and_both_benchmarks(self):
  x=evaluate(decision(),bars("A",100,110)+bars("SPY",100,101)+bars("VOO",100,102),max_positions=2,cost_bps=20)
  self.assertEqual(x["status"],"ILLUSTRATIVE_NOT_EXECUTED")
  self.assertAlmostEqual(x["net_return"],.049)
  self.assertAlmostEqual(x["cash_weight"],.5)
  self.assertTrue(x["beat_both"])
 def test_missing_voo_blocks(self):
  x=evaluate(decision(),bars("A",100,110)+bars("SPY",100,101))
  self.assertEqual(x["status"],"BLOCKED_MISSING_BARS")
  self.assertIn("VOO",x["missing"])
 def test_misaligned_dates_block(self):
  b=bars("A",100,110)+bars("SPY",100,101)+bars("VOO",100,102)
  b[-1]["session_close_at"]="2020-03-05T21:00:00Z"
  self.assertEqual(evaluate(decision(),b)["status"],"BLOCKED_UNALIGNED_SESSIONS")
 def test_future_decision_no_same_day_fills(self):
  b=bars("A",100,110)+bars("SPY",100,101)+bars("VOO",100,102)
  for row in b:
   row["session_open_at"]="2020-03-02T14:30:00Z"
  self.assertEqual(evaluate(decision(),b)["status"],"BLOCKED_MISSING_BARS")
if __name__=="__main__":unittest.main()
