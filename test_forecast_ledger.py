import sqlite3
import unittest
from forecast_ledger import freeze,score,summary

class ForecastLedgerTests(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(":memory:")
  self.forecast={"symbol":"TEST","frozen_at":"2026-11-10T15:00:00Z",
   "evidence_cutoff":"2026-11-10T14:00:00Z","direction":"LONG",
   "entry_price":100,"entry_band":[99,101],"invalidation":95,
   "horizon":"2 sessions","horizon_sessions":2,"benchmark":"SPY",
   "costs":"10 bps","cost_bps":10,"source_receipts":["sec-verified-receipt"]}
 def test_freeze_is_immutable(self):
  first=freeze(self.db,self.forecast)
  self.assertEqual(first["status"],"FROZEN")
  self.assertEqual(freeze(self.db,self.forecast)["status"],"EXISTS")
  with self.assertRaises(sqlite3.DatabaseError):
   self.db.execute("DELETE FROM shadow_forecasts")
 def test_lookahead_rejected(self):
  x=dict(self.forecast,evidence_cutoff="2026-11-11T00:00:00Z")
  self.assertEqual(freeze(self.db,x)["status"],"REJECTED")
 def test_scoring_waits_for_horizon_and_deduplicates(self):
  fid=freeze(self.db,self.forecast)["forecast_id"]
  obs=[{"date":"2026-11-11","close":102,"benchmark_return":.01,"price_source":"licensed feed","benchmark_source":"licensed feed"},
   {"date":"2026-11-12","close":110,"benchmark_return":.03,"price_source":"licensed feed","benchmark_source":"licensed feed"}]
  self.assertEqual(score(self.db,fid,obs[:1],"2026-11-13T00:00:00Z")["status"],"PENDING_HORIZON")
  self.assertEqual(score(self.db,fid,obs,"2026-11-13T00:00:00Z")["status"],"SCORED")
  self.assertEqual(score(self.db,fid,obs,"2026-11-13T00:00:00Z")["status"],"EXISTS")
  self.assertEqual(summary(self.db)["scored"],1)
  with self.assertRaises(sqlite3.DatabaseError):
   self.db.execute("UPDATE shadow_outcomes SET outcome_json='{}'")
 def test_missing_evidence_rejected(self):
  self.assertEqual(freeze(self.db,dict(self.forecast,source_receipts=[]))["status"],"REJECTED")
if __name__=="__main__":unittest.main()
