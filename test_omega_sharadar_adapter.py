import csv,tempfile,unittest
from pathlib import Path
from omega_sharadar_adapter import convert
class SharadarAdapterTests(unittest.TestCase):
 def test_preserves_delisted_symbol_and_filters_period(self):
  with tempfile.TemporaryDirectory() as d:
   source=Path(d)/"sep.csv";target=Path(d)/"normalized.csv"
   with source.open("w",newline="") as f:
    w=csv.writer(f);w.writerow(["ticker","date","open","high","low","close","volume"])
    w.writerow(["DELISTED_OLD","2015-01-05",10,12,9,11,100])
    w.writerow(["NEW","2026-01-05",10,12,9,11,100])
   r=convert(source,target)
   self.assertEqual(r["rows"],1)
   with target.open(newline="") as f:
    rows=list(csv.DictReader(f))
   self.assertEqual(rows[0]["symbol"],"DELISTED_OLD")
   self.assertEqual(len(rows),1)
 def test_missing_columns_fail(self):
  with tempfile.TemporaryDirectory() as d:
   source=Path(d)/"bad.csv";target=Path(d)/"out.csv"
   source.write_text("ticker,date\nA,2015-01-05\n")
   with self.assertRaises(ValueError):convert(source,target)
if __name__=="__main__":unittest.main()
