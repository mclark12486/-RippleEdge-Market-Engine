import unittest
from omega_paper_engine import initial,step,digest
SIG={"symbol":"ABC","score":5,"upside":.12,"downside":.04,
     "evidence_verified":True,"frozen_before_session":True}
class PaperTests(unittest.TestCase):
 def test_separate_virtual_account_and_buy(self):
  s=step(initial(),"2026-11-12",{"ABC":100},[SIG])
  self.assertEqual(s["positions"]["ABC"],4)
  self.assertEqual(s["ledger"][0]["execution"],"SIMULATED_CLOSE_ONLY_NOT_LIVE")
 def test_unverified_signal_passes(self):
  s=step(initial(),"2026-11-12",{"ABC":100},[{**SIG,"evidence_verified":False}])
  self.assertEqual(s["positions"],{})
 def test_crash_not_erased(self):
  s=step(initial(),"2026-11-12",{"ABC":100},[SIG])
  s=step(s,"2026-11-13",{"ABC":10},[])
  self.assertLess(s["equity"],10000)
  self.assertEqual(s["positions"],{})
  self.assertEqual(s["ledger"][-1]["risk"],"EMERGENCY_REVIEW")
 def test_replay_rejected(self):
  s=step(initial(),"2026-11-12",{"ABC":100},[])
  with self.assertRaises(ValueError):step(s,"2026-11-12",{"ABC":100},[])
 def test_missing_held_quote_fails_closed(self):
  s=step(initial(),"2026-11-12",{"ABC":100},[SIG])
  with self.assertRaises(ValueError):step(s,"2026-11-13",{"DEF":10},[])
 def test_receipts_are_deterministic(self):
  a=step(initial(),"2026-11-12",{"ABC":100},[SIG])
  b=step(initial(),"2026-11-12",{"ABC":100},[SIG])
  self.assertEqual(digest(a),digest(b))
if __name__=="__main__":unittest.main()
