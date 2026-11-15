import datetime as dt,unittest
from omega_free_strategy_pilot import SYMBOLS,run
class PilotTests(unittest.TestCase):
 def test_valid_synthetic_is_labeled_biased(self):
  day=dt.date(2015,1,2)
  dates=[(day+dt.timedelta(days=i)).isoformat() for i in range(4020)]
  bars={s:[(d,100+i*.01,100+i*.01) for i,d in enumerate(dates)] for s in SYMBOLS}
  r=run(bars)
  self.assertEqual(r["status"],"ILLUSTRATIVE_SURVIVORSHIP_BIASED_NOT_VALIDATED")
  self.assertIsNone(r["rippleedge_production_return"])
 def test_missing_history_rejected(self):
  bars={s:[("2025-12-31",100,101)] for s in SYMBOLS}
  with self.assertRaises(ValueError):run(bars)
if __name__=="__main__":unittest.main()
