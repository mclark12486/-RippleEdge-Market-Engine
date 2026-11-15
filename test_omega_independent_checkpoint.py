import json,tempfile,unittest
from pathlib import Path
from omega_independent_checkpoint import checkpoint
class CheckpointTests(unittest.TestCase):
 def test_initial_cash_and_idempotent_session(self):
  with tempfile.TemporaryDirectory() as d:
   s=Path(d)/"s.json";r=Path(d)/"r.json"
   f=lambda:{"session":"2026-11-13","prices":{"SPY":650},"spy_return":.01}
   first=checkpoint(f,s,r)
   self.assertEqual(first["status"],"SHADOW_CASH_ONLY")
   self.assertEqual(first["positions"],{})
   self.assertEqual(checkpoint(f,s,r)["status"],"NO_NEW_SESSION")
   self.assertEqual(len(json.loads(s.read_text())["ledger"]),1)
 def test_missing_data_does_not_create_state(self):
  with tempfile.TemporaryDirectory() as d:
   s=Path(d)/"s.json"
   self.assertEqual(checkpoint(lambda:{},s,Path(d)/"r.json")["status"],"DATA_BLOCKED")
   self.assertFalse(s.exists())
 def test_next_session_preserves_cash(self):
  with tempfile.TemporaryDirectory() as d:
   s=Path(d)/"s.json";r=Path(d)/"r.json"
   for date in ("2026-11-12","2026-11-13"):
    checkpoint(lambda date=date:{"session":date,"prices":{"SPY":650},"spy_return":-.03},s,r)
   self.assertEqual(json.loads(s.read_text())["cash"],100)
if __name__=="__main__":unittest.main()
