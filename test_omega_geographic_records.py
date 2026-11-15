import unittest
from omega_geographic_records import scan,stable_id,socrata_url,JURISDICTIONS
from omega_entity_resolution import enrich,matches
class GeographicTests(unittest.TestCase):
 def test_dedup_and_provenance(self):
  x=scan("Acme Industrial",["chicago_building_permits"],
   lambda url:[{"id":"123","owner":"Acme Industrial LLC"},{"id":"123","owner":"Acme Industrial LLC"}])
  self.assertEqual(len(x["records"]),1)
  self.assertFalse(x["trade_eligible"])
  self.assertEqual(x["verified_company_links"],0)
 def test_partial_outage_not_hidden(self):
  def f(url):
   if "chicago" in url:raise TimeoutError("offline")
   return [{"id":"999"}]
  x=scan("Acme Industrial",fetch=f)
  self.assertEqual(x["status"],"PARTIAL")
  self.assertEqual(x["jurisdictions"]["chicago_building_permits"]["status"],"BLOCKED")
 def test_alias_is_not_verified(self):
  r=enrich([{"record":{"owner":"Acme Industrial LLC"}}],{"ACME":["Acme Industrial LLC"]})
  self.assertEqual(r[0]["potential_mentions"][0]["ticker"],"ACME")
  self.assertFalse(r[0]["potential_mentions"][0]["entity_verified"])
  self.assertFalse(r[0]["trade_eligible"])
 def test_short_ambiguous_alias_ignored(self):
  self.assertEqual(matches({"owner":"ABC LLC"},["ABC"]),[])
if __name__=="__main__":unittest.main()
