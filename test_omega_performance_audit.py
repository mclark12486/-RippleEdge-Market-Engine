import unittest
from omega_performance_audit import metrics,compare
class PerformanceTests(unittest.TestCase):
 def test_loss_is_reported(self):
  x=metrics([100,95,98])
  self.assertAlmostEqual(x["worst_session_return"],-.05)
  self.assertAlmostEqual(x["max_drawdown"],.05)
  self.assertEqual(x["losing_sessions"],1)
 def test_alignment(self):
  with self.assertRaises(ValueError):compare([100,101,102],{"SPY":[100,101]})
 def test_bad_equity(self):
  with self.assertRaises(ValueError):metrics([100,0,110])
if __name__=="__main__":unittest.main()
