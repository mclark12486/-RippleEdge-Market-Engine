import unittest
import urllib.error
from omega_entitlement_probe import probe
class EntitlementTests(unittest.TestCase):
 def test_all_sample_endpoints_accessible(self):
  r=probe(lambda path:{"status":"OK","results":[{"T":"SPY"}]})
  self.assertTrue(r["all_accessible"])
  self.assertEqual(len(r["checks"]),6)
  self.assertEqual(r["status"],"SAMPLE_ENDPOINTS_ACCESSIBLE_NOT_DATA_VALIDATED")
 def test_rejected_2015_does_not_claim_access(self):
  def fetch(path):
   if "2015" in path:raise urllib.error.HTTPError(path,403,"Forbidden",{},None)
   return {"status":"OK","results":[{"T":"SPY"}]}
  r=probe(fetch)
  self.assertFalse(r["all_accessible"])
  self.assertEqual(r["status"],"HISTORICAL_ACCESS_INCOMPLETE")
  self.assertTrue(any(x.get("http_status")==403 for x in r["checks"]))
 def test_empty_results_do_not_count(self):
  r=probe(lambda path:{"status":"OK","results":[]})
  self.assertFalse(r["all_accessible"])
if __name__=="__main__":unittest.main()
