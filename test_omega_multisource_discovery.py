import unittest
from omega_multisource_discovery import scan_company
def fake(url,*,payload=None):
 if "clinicaltrials" in url:return {"studies":[{"protocolSection":{"identificationModule":{"nctId":"NCT123","briefTitle":"Trial A"}}}]}
 if "federalregister" in url:return {"results":[{"document_number":"2026-01","title":"Rule"}]}
 if "europepmc" in url:return {"resultList":{"result":[{"id":"123","title":"Paper"}]}}
 return {"results":[{"Award ID":"1234","Recipient Name":"Acme","Award Amount":100}]}
class DiscoveryTests(unittest.TestCase):
 def test_four_independent_sources(self):
  x=scan_company("Acme Biotech",fake)
  self.assertEqual(len(x["events"]),4)
  self.assertEqual(len(x["sources"]),4)
  self.assertTrue(all(e["relationship"]=="UNVERIFIED_NAME_SEARCH" for e in x["events"]))
 def test_partial_failure_explicit(self):
  def fail(url,*,payload=None):
   if "europepmc" in url:raise TimeoutError("unavailable")
   return fake(url,payload=payload)
  x=scan_company("Acme Biotech",fail)
  self.assertEqual(x["status"],"PARTIAL")
  self.assertEqual(x["sources"]["research"]["status"],"BLOCKED")
 def test_short_name_rejected(self):
  with self.assertRaises(ValueError):scan_company("X",fake)
if __name__=="__main__":unittest.main()
