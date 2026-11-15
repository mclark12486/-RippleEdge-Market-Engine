import unittest
from omega_walkforward import compare

def series(symbol,values):
 return [(f"2020-01-{i+1:02d}",float(x),float(x)) for i,x in enumerate(values)]
class WalkforwardTests(unittest.TestCase):
 def test_future_winner_not_selected(self):
  data={"SPY":series("SPY",[100]*12),"VOO":series("VOO",[100]*12),
   "A":series("A",[100,101,102,103,104,105,106,107,108,109,110,111]),
   "B":series("B",[100,100,100,100,100,100,100,100,100,100,1000,1000])}
  r=compare(data,lookback=3,hold=2)
  self.assertEqual(r["status"],"EXPLORATORY_UNVALIDATED")
  self.assertEqual(r["trades"][0]["symbol"],"A")
  self.assertIn("spy_compounded",r)
  self.assertIn("voo_compounded",r)
 def test_missing_bars_blocks(self):
  with self.assertRaises(ValueError):
   compare({"SPY":series("SPY",[100]*12),"VOO":series("VOO",[100]*11),"A":series("A",[100]*12)})
 def test_missing_benchmark_blocks(self):
  with self.assertRaises(ValueError):compare({"SPY":series("SPY",[100]*12)})
if __name__=="__main__":unittest.main()
