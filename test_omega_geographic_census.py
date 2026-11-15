import unittest
from omega_geographic_census import checkpoint
C=[{"symbol":"A","name":"Alpha Holdings"},{"symbol":"B","name":"Bravo Industries"}]
def scanner(name,jurisdictions):
 j=jurisdictions[0]
 return {"jurisdictions":{j:{"status":"SEARCH_OK_NOT_COMPLETENESS_VERIFIED","records":1}},
 "records":[{"id":"123","record":{"owner":name},"trade_eligible":False}]}
class CensusTests(unittest.TestCase):
 def test_full_rotation_and_coverage(self):
  a=checkpoint(C,batch_size=2,scanner=scanner)
  self.assertEqual(a["configured_pairs"],4)
  self.assertEqual(a["configured_pair_attempt_coverage"],.5)
  b=checkpoint(C,prior=a,batch_size=2,scanner=scanner)
  self.assertEqual(b["configured_pair_attempt_coverage"],1)
  self.assertEqual(b["cursor"],0)
  self.assertFalse(b["trade_eligible"])
 def test_failed_source_counted_not_success(self):
  def fail(name,jurisdictions):
   j=jurisdictions[0]
   return {"jurisdictions":{j:{"status":"BLOCKED"}},"records":[]}
  x=checkpoint(C,batch_size=1,scanner=fail)
  self.assertEqual(x["failed_queries_this_run"],1)
  self.assertEqual(x["successful_queries_this_run"],0)
  self.assertEqual(x["unique_pairs_attempted"],1)
 def test_invalid_jurisdiction_rejected(self):
  with self.assertRaises(ValueError):checkpoint(C,["imaginary"],scanner=scanner)
if __name__=="__main__":unittest.main()
