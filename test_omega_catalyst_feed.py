import unittest
from omega_catalyst_registry import classify_sec,coverage
from omega_catalyst_feed import checkpoint
FEED=b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><id>filing-1</id><title>8-K - ACME</title><updated>2026-11-15T12:00:00Z</updated></entry></feed>'''
class CatalystTests(unittest.TestCase):
 def test_form_not_transaction_confirmation(self):
  x=classify_sec("8-K - ACME")
  self.assertIn("mergers_acquisitions",x["candidate_categories"])
  self.assertFalse(x["event_confirmed"])
 def test_patents_and_litigation_not_falsely_covered(self):
  c=coverage()
  self.assertEqual(c["categories"]["patents_ip"]["status"],"NOT_CONNECTED")
  self.assertFalse(c["marketwide_all_categories_verified"])
 def test_feed_dedup(self):
  a=checkpoint(FEED)
  self.assertEqual(a["new_filings"],1)
  b=checkpoint(FEED,a)
  self.assertEqual(b["new_filings"],0)
if __name__=="__main__":unittest.main()
