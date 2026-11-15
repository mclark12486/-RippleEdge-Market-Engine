import unittest
from omega_geographic_records import stable_id
class PermitIdentityTests(unittest.TestCase):
 def test_nyc_job_not_unique(self):
  a={"job__":"100","job_doc___":"01","permit_sequence__":"01","permit_si_no":"123"}
  b={**a,"permit_si_no":"124"}
  self.assertNotEqual(stable_id("nyc_dob_permits",a),stable_id("nyc_dob_permits",b))
 def test_chicago_stable_on_updates(self):
  a={"id":"ABC","work_description":"old"}
  b={**a,"work_description":"new"}
  self.assertEqual(stable_id("chicago_building_permits",a),stable_id("chicago_building_permits",b))
 def test_incomplete_key_does_not_collapse(self):
  a={"job__":"100","permit_status":"issued"}
  b={**a,"permit_status":"expired"}
  self.assertNotEqual(stable_id("nyc_dob_permits",a),stable_id("nyc_dob_permits",b))
if __name__=="__main__":unittest.main()
