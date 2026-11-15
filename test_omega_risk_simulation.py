import unittest
from omega_risk_simulation import simulate
class RiskSimulationTests(unittest.TestCase):
 def test_cannot_erase_initial_loss(self):
  r=simulate([-.05,.02,.02,.02,.02,.02],[0]*6)
  self.assertEqual(r["max_daily_loss_fraction"],-.05)
  self.assertEqual(r["events"][0]["effective"],"NEXT_SESSION")
 def test_small_red_no_trigger(self):
  r=simulate([-.004,.003,.002],[0]*3)
  self.assertEqual(len(r["events"]),0)
 def test_invalid_rejected(self):
  with self.assertRaises(ValueError):simulate([.1],[.1])
if __name__=="__main__":unittest.main()
