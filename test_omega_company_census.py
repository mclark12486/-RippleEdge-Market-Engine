import unittest
from omega_company_census import census
from omega_evidence_graph import build_graph,rank_for_review
COMP=[{"symbol":"A","name":"Acme Corp"},{"symbol":"B","name":"Bravo Corp"},{"symbol":"C","name":"Charlie Corp"}]
def fake(name):
 return {"status":"SEARCH_COMPLETE_ENTITY_UNVERIFIED","sources":{"research":{"status":"SEARCH_OK_NOT_ENTITY_VERIFIED"}},
 "events":[{"id":"123","source":"research","title":"Related paper"}]}
class CensusTests(unittest.TestCase):
 def test_rotation_and_coverage(self):
  a=census(COMP,batch_size=2,scanner=fake)
  self.assertEqual(a["batch_coverage"],2/3)
  b=census(COMP,a,batch_size=2,scanner=fake)
  self.assertEqual([r["symbol"] for r in b["records"]],["C","A"])
  self.assertFalse(b["trade_eligible"])
 def test_graph_never_claims_confirmed_link(self):
  g=build_graph("Acme",fake("Acme")["events"])
  self.assertEqual(g["verified_company_relationships"],0)
  self.assertFalse(g["trade_eligible"])
  self.assertEqual(rank_for_review(g)[0]["status"],"NEEDS_ENTITY_AND_MATERIALITY_VERIFICATION")
 def test_source_failure_is_recorded(self):
  def fail(name):raise TimeoutError("down")
  r=census(COMP,batch_size=1,scanner=fail)
  self.assertEqual(r["batch_checked"],0)
  self.assertEqual(r["records"][0]["status"],"BLOCKED")
if __name__=="__main__":unittest.main()
