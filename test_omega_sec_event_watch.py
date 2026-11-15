import unittest
from omega_sec_event_watch import check,parse_atom
ATOM=b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><id>urn:filing:1</id><title>8-K Example</title><updated>2026-11-15T12:00:00Z</updated></entry></feed>'''
class WatchTests(unittest.TestCase):
 def test_first_seen(self):
  x=check(lambda:ATOM,now="2026-11-15T12:01:00Z")
  self.assertEqual(x["new_entries"],1)
  self.assertEqual(x["status"],"POLL_SUCCESS_PARTIAL_FEED")
 def test_duplicate_not_reannounced(self):
  x=check(lambda:ATOM)
  y=check(lambda:ATOM,x)
  self.assertEqual(y["new_entries"],0)
 def test_invalid_feed_fails(self):
  with self.assertRaises(ValueError):check(lambda:b"<html></html>")
if __name__=="__main__":unittest.main()
