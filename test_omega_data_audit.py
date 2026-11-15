import sqlite3
import unittest
from omega_data_audit import audit
class FullCycleReadinessTests(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(":memory:")
  self.db.execute("CREATE TABLE daily_bars(symbol TEXT,session TEXT)")
 def tearDown(self):self.db.close()
 def test_empty_database_blocks(self):
  r=audit(self.db)
  self.assertEqual(r["status"],"BLOCKED_UNVERIFIED_DATA")
  self.assertIsNone(r["strategy_results"])
 def test_partial_history_blocks(self):
  self.db.executemany("INSERT INTO daily_bars VALUES(?,?)",[("SPY","2025-12-31"),("VOO","2025-12-31")])
  r=audit(self.db)
  self.assertIn("Full 2015-2025 daily history not present",r["limitations"])
 def test_missing_voo_detected(self):
  self.db.execute("INSERT INTO daily_bars VALUES('SPY','2015-01-05')")
  r=audit(self.db)
  self.assertEqual(r["missing_benchmark_sessions"],1)
 def test_unsubstantiated_claim_rejected(self):
  r=audit(self.db,{"security_universe_verified":{"verified":True}})
  self.assertFalse(r["security_universe_verified"])
if __name__=="__main__":unittest.main()
