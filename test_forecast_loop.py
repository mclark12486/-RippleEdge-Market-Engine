import datetime as dt
import sqlite3
import unittest
from forecast_loop import run

class ForecastLoopTests(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(":memory:")
  self.db.executescript("""
   CREATE TABLE price_runs(run_id TEXT,checked_at TEXT,provider TEXT,session TEXT,requested INT,returned INT,matched INT,missing INT,unmatched INT,status TEXT,receipt TEXT);
   CREATE TABLE daily_bars(symbol TEXT,session TEXT,open REAL,high REAL,low REAL,close REAL,volume REAL,provider TEXT,first_seen TEXT);
   CREATE TABLE breadth_signals(id INTEGER PRIMARY KEY,symbol TEXT,run_id TEXT,session TEXT,signal TEXT,metric REAL,baseline_sessions INT,observed_at TEXT);
  """)
  self.current=dt.datetime(2026,11,16,15,0,tzinfo=dt.timezone.utc)
 def seed(self):
  self.db.execute("INSERT INTO price_runs VALUES(?,?,?,?,?,?,?,?,?,?,?)",("r","2026-11-16T12:00:00Z","Massive/Polygon","2026-11-13",2,2,2,0,0,"DAILY_BAR_CENSUS_MATCHED","{}"))
  for sym,close in (("SPY",600),("VOO",550),("TEST",100)):
   self.db.execute("INSERT INTO daily_bars VALUES(?,?,?,?,?,?,?,?,?)",(sym,"2026-11-13",close,close,close,close,1000,"Massive/Polygon","2026-11-16"))
  self.db.execute("INSERT INTO breadth_signals(symbol,run_id,session,signal,metric,baseline_sessions,observed_at) VALUES(?,?,?,?,?,?,?)",("TEST","r","2026-11-13","RELATIVE_VOLUME",4.2,20,"2026-11-16"))
 def test_blocked_without_feed(self):
  self.assertEqual(run(self.db,self.current)["status"],"BLOCKED")
 def test_freeze_once_then_score_only_future_bars(self):
  self.seed()
  first=run(self.db,self.current)
  self.assertEqual(first["new_forecasts"],1)
  self.assertEqual(first["outcomes_scored"],0)
  self.assertEqual(run(self.db,self.current)["new_forecasts"],0)
  for n,day in enumerate(("2026-11-17","2026-11-18","2026-11-19","2026-11-20","2026-11-23"),1):
   for sym,close in (("SPY",600+n),("VOO",550+n),("TEST",100+n)):
    self.db.execute("INSERT INTO daily_bars VALUES(?,?,?,?,?,?,?,?,?)",(sym,day,close,close,close,close,1000,"Massive/Polygon","2026-11-24"))
  # A later actual run may score only after all five sessions have elapsed.
  self.db.execute("INSERT INTO price_runs VALUES(?,?,?,?,?,?,?,?,?,?,?)",("r2","2026-11-24T12:00:00Z","Massive/Polygon","2026-11-23",2,2,2,0,0,"DAILY_BAR_CENSUS_MATCHED","{}"))
  later=dt.datetime(2026,11,24,15,0,tzinfo=dt.timezone.utc)
  self.assertEqual(run(self.db,later)["outcomes_scored"],1)
  self.assertEqual(run(self.db,later)["outcomes_scored"],0)
  self.assertEqual(self.db.execute("SELECT COUNT(*) FROM shadow_outcomes").fetchone()[0],1)
  import json
  result=json.loads(self.db.execute("SELECT outcome_json FROM shadow_outcomes").fetchone()[0])
  self.assertIn("excess_vs_voo",result)
  self.assertIn("beat_both",result)
 def test_missing_benchmark_blocks(self):
  self.seed()
  self.db.execute("DELETE FROM daily_bars WHERE symbol='SPY'")
  self.assertEqual(run(self.db,self.current)["status"],"BLOCKED")
if __name__=="__main__":unittest.main()
