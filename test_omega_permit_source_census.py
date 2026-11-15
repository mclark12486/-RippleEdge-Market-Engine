import unittest
from omega_permit_source_census import census,count_url
class CountTests(unittest.TestCase):
 def test_count_url(self):
  u=count_url({"host":"data.example.org","dataset":"abcd-1234"})
  self.assertIn("count%28%2A%29",u)
 def test_counts_not_completeness(self):
  r=census(fetch=lambda url:[{"count":"1000"}])
  self.assertEqual(len(r["sources"]),2)
  self.assertFalse(r["historical_completeness_verified"])
  self.assertTrue(all(s["reported_rows"]==1000 for s in r["sources"].values()))
 def test_failure_visible(self):
  r=census(fetch=lambda url:(_ for _ in ()).throw(TimeoutError("slow")))
  self.assertTrue(all(s["status"]=="COUNT_FAILED" for s in r["sources"].values()))
if __name__=="__main__":unittest.main()
