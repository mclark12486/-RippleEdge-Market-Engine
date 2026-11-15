import datetime as dt,unittest
from omega_portfolio_monitor import monitor
NOW=dt.datetime(2026,11,15,16,0,tzinfo=dt.timezone.utc)
BASE={"asof":"2026-11-15T15:59:00Z","source":"broker_verified",
      "equity":9500,"previous_close_equity":10000,"peak_equity":10500,
      "market_day_return":-.02,"estimated_gap_risk":.04,
      "positions":[{"symbol":"ABC","market_value":3000,"thesis_broken":False}]}
class MonitorTests(unittest.TestCase):
 def test_emergency_generates_paper_review_not_order(self):
  r=monitor(BASE,NOW)
  self.assertEqual(r["risk"]["action"],"EMERGENCY_REVIEW")
  self.assertEqual(r["paper_orders"][0]["execution"],"NONE_PAPER_ONLY")
 def test_stale_blocks(self):
  r=monitor({**BASE,"asof":"2026-11-15T14:00:00Z"},NOW)
  self.assertEqual(r["paper_orders"],[])
  self.assertEqual(r["status"],"BLOCKED_STALE_OR_UNVERIFIED")
 def test_manual_unverified_rejected(self):
  r=monitor({**BASE,"source":"unknown"},NOW)
  self.assertEqual(r["paper_orders"],[])
 def test_no_snapshot_blocks(self):
  self.assertEqual(monitor({},NOW)["status"],"BLOCKED_MISSING_PORTFOLIO_DATA")
 def test_minor_red_does_not_panic_sell(self):
  r=monitor({**BASE,"equity":9990,"peak_equity":10000,"estimated_gap_risk":.001,"market_day_return":0},NOW)
  self.assertEqual(r["risk"]["action"],"HOLD_OR_RESEARCH")
  self.assertEqual(r["paper_orders"],[])
if __name__=="__main__":unittest.main()
