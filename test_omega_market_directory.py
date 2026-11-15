import unittest
from omega_market_directory import build
class DirectoryTests(unittest.TestCase):
 def test_cik_identity_and_dedup(self):
  rows,receipt=build({"0":{"ticker":"ABC","title":"ABC Corp","cik_str":123},
   "1":{"ticker":"ABC","title":"ABC Corp","cik_str":123},
   "2":{"ticker":"XYZ","title":"XYZ Inc","cik_str":987}})
  self.assertEqual(len(rows),2)
  self.assertEqual(rows[0]["cik"],"0000000123")
  self.assertEqual(receipt["rejected_records"],1)
  self.assertFalse(receipt["marketwide_complete"])
 def test_empty_rejected(self):
  with self.assertRaises(ValueError):build({})
if __name__=="__main__":unittest.main()
