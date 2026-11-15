import unittest
from omega_permit_coverage_comparison import compare
from omega_permit_schema_inspection import inspect
class CoverageTests(unittest.TestCase):
 def test_fraction_not_false_completeness(self):
  r=compare({"sources":{"a":{"unique_records_seen_in_window":70}}},{"sources":{"a":{"status":"COUNT_OK","reported_rows":1000}}})
  self.assertEqual(r["sources"]["a"]["observed_fraction_lower_bound"],.07)
  self.assertFalse(r["historical_completeness_verified"])
 def test_schema_candidates_not_verified_watermark(self):
  r=inspect(fetch=lambda url:[{"permit_number":"123","last_updated":"2026-11-15","issued_date":"2020-01-01"}])
  self.assertTrue(all("last_updated" in x["candidate_timestamp_fields"] for x in r["sources"].values()))
  self.assertTrue(all(not x["provider_update_field_validated"] for x in r["sources"].values()))
if __name__=="__main__":unittest.main()
