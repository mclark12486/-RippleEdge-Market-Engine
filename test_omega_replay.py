import unittest
from omega_replay import snapshot_at,freeze_decision,next_session_return

T="2020-03-02T16:00:00Z"
def rec(symbol,pub,seen,value):
 return {"symbol":symbol,"published_at":pub,"ingested_at":seen,"source_id":symbol+str(value),"value":value}
class ReplayTests(unittest.TestCase):
 def test_future_publication_and_late_ingestion_excluded(self):
  rows=[rec("A","2020-03-02T15:00:00Z","2020-03-02T15:01:00Z",1),
        rec("A","2020-03-03T15:00:00Z","2020-03-03T15:01:00Z",99),
        rec("B","2020-03-01T15:00:00Z","2020-03-03T15:01:00Z",88)]
  x=snapshot_at(rows,T)
  self.assertEqual([r["value"] for r in x],[1])
 def test_future_winner_cannot_be_selected(self):
  rows=[rec("A","2020-03-02T15:00:00Z","2020-03-02T15:01:00Z",1),
        rec("WINNER","2020-03-03T15:00:00Z","2020-03-03T15:01:00Z",100)]
  with self.assertRaises(ValueError):
   freeze_decision(rows,T,lambda r:["WINNER"],"omega-0")
 def test_next_session_only_and_costs(self):
  d=freeze_decision([rec("A","2020-03-02T15:00:00Z","2020-03-02T15:01:00Z",1)],T,lambda r:["A"],"omega-0")
  bars=[{"symbol":"A","session_open_at":"2020-03-02T14:30:00Z","session_close_at":"2020-03-02T21:00:00Z","open":1,"close":999},
        {"symbol":"A","session_open_at":"2020-03-03T14:30:00Z","session_close_at":"2020-03-03T21:00:00Z","open":100,"close":102},
        {"symbol":"A","session_open_at":"2020-03-04T14:30:00Z","session_close_at":"2020-03-04T21:00:00Z","open":101,"close":110}]
  x=next_session_return(d,bars,"A",20)
  self.assertEqual(x["entry_session"],"2020-03-03T14:30:00Z")
  self.assertAlmostEqual(x["net_return"],.098)
 def test_naive_timestamp_rejected(self):
  with self.assertRaises(ValueError):snapshot_at([], "2020-01-01T12:00:00")
if __name__=="__main__":unittest.main()
