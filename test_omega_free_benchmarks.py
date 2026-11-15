import unittest
from omega_free_benchmarks import evaluate
class FreeBenchmarkTests(unittest.TestCase):
 def test_missing_data_is_not_performance(self):
  result=evaluate({"SPY":[]})
  self.assertIsNone(result["rippleedge_return"])
  self.assertEqual(result["comparison"]["SPY"]["status"],"INSUFFICIENT_COVERAGE")
 def test_benchmark_return_is_computed_not_fabricated(self):
  import datetime as dt
  start=dt.date(2015,1,2)
  rows=[((start+dt.timedelta(days=i)).isoformat(),100+i/100) for i in range(4015)]
  result=evaluate({"SPY":rows})
  self.assertEqual(result["comparison"]["SPY"]["status"],"EXPLORATORY")
  self.assertGreater(result["comparison"]["SPY"]["total_return_percent"],0)
  self.assertIsNone(result["rippleedge_return"])
if __name__=="__main__":unittest.main()
