import unittest
from omega_incremental_permits import ingest,mentions,page_url
INDEX={"industrial":[("acme industrial","ACME","0000000123")]}
class IncrementalTests(unittest.TestCase):
 def test_source_page_not_company_query(self):
  url=page_url({"host":"data.example.org","dataset":"abcd-1234"},25,10)
  self.assertIn("%24offset=25",url)
  self.assertNotIn("%24q=",url)
 def test_match_and_no_trade(self):
  hits=mentions({"owner":"Acme Industrial LLC"},INDEX)
  self.assertEqual(hits[0]["symbol"],"ACME")
  self.assertFalse(hits[0]["ownership_verified"])
  self.assertFalse(hits[0]["trade_eligible"])
 def test_paging_dedup_and_end_of_sweep(self):
  calls=[]
  def fetch(url):
   calls.append(url)
   return [{"id":"one","owner":"Acme Industrial"},{"id":"two","owner":"Other"}] if "%24offset=0" in url else []
  a=ingest(None,INDEX,["chicago_building_permits"],fetch=fetch,limit=2)
  self.assertEqual(a["new_records_this_run"],2)
  self.assertEqual(a["potential_company_mentions_this_run"],1)
  self.assertEqual(a["sources"]["chicago_building_permits"]["offset"],2)
  b=ingest(a,INDEX,["chicago_building_permits"],fetch=fetch,limit=2)
  self.assertEqual(b["new_records_this_run"],0)
  self.assertEqual(b["sources"]["chicago_building_permits"]["offset"],0)
  c=ingest(b,INDEX,["chicago_building_permits"],fetch=fetch,limit=2)
  self.assertEqual(c["new_records_this_run"],0)
 def test_overlap_detects_modified_record(self):
  pages=[
   [{"id":"one","owner":"Acme Industrial"},{"id":"two","owner":"Other"}],
   [{"id":"two","owner":"Acme Industrial revised"}]]
  def fetch(url):return pages[0] if "%24offset=0" in url else pages[1]
  a=ingest(None,INDEX,["chicago_building_permits"],fetch=fetch,limit=2,overlap=1)
  b=ingest(a,INDEX,["chicago_building_permits"],fetch=fetch,limit=2,overlap=1)
  self.assertEqual(b["modified_records_this_run"],1)
  self.assertEqual(b["new_records_this_run"],0)
 def test_reconciliation_resets_offset(self):
  calls=[]
  def fetch(url):
   calls.append(url)
   return [{"id":"one"},{"id":"two"}]
  a=ingest(None,INDEX,["chicago_building_permits"],fetch=fetch,limit=2,reconcile_every=1)
  b=ingest(a,INDEX,["chicago_building_permits"],fetch=fetch,limit=2,reconcile_every=1)
  self.assertIn("%24offset=0",calls[-1])
  self.assertEqual(b["reconciliations_started_this_run"],1)
 def test_failure_keeps_cursor(self):
  a=ingest(None,INDEX,["chicago_building_permits"],fetch=lambda url:(_ for _ in ()).throw(TimeoutError()),limit=2)
  self.assertEqual(a["source_failures"],1)
  self.assertEqual(a["sources"]["chicago_building_permits"]["status"],"PAGE_FETCH_FAILED")
if __name__=="__main__":unittest.main()
