import csv,tempfile,unittest,sqlite3
from pathlib import Path
from omega_historical_import import import_csv,FIELDS
class HistoricalImportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.csv=Path(self.tmp.name)/"sample.csv"
  self.db=Path(self.tmp.name)/"history.sqlite"
 def tearDown(self):self.tmp.cleanup()
 def write(self,rows):
  with self.csv.open("w",newline="") as f:
   w=csv.writer(f);w.writerow(FIELDS);w.writerows(rows)
 def row(self,day="2015-01-05",symbol="DELISTED",close=11):
  return [day,symbol,10,12,9,close,100,"licensed-dataset-record"]
 def test_import_preserves_delisted_and_hash(self):
  self.write([self.row(),self.row(symbol="SPY")])
  r=import_csv(self.csv,self.db,"licensed-source")
  self.assertEqual(r["rows_imported"],2)
  self.assertEqual(len(r["file_sha256"]),64)
  with sqlite3.connect(self.db) as c:
   self.assertEqual(c.execute("SELECT COUNT(*) FROM historical_bars WHERE symbol='DELISTED'").fetchone()[0],1)
 def test_collision_rejected_without_replacement(self):
  self.write([self.row()])
  import_csv(self.csv,self.db,"licensed-source")
  with self.assertRaises(sqlite3.IntegrityError):import_csv(self.csv,self.db,"licensed-source")
 def test_invalid_price_rejected(self):
  self.write([self.row(close=15)])
  with self.assertRaises(ValueError):import_csv(self.csv,self.db,"licensed-source")
 def test_outside_range_rejected(self):
  self.write([self.row(day="2026-01-05")])
  with self.assertRaises(ValueError):import_csv(self.csv,self.db,"licensed-source")
 def test_duplicate_rows_rejected(self):
  self.write([self.row(),self.row()])
  with self.assertRaises(ValueError):import_csv(self.csv,self.db,"licensed-source")
if __name__=="__main__":unittest.main()
