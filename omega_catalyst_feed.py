"""Market-wide SEC feed event router with dedup and source-specific coverage.

Runs once per feed, not once per ticker. The SEC current filings feed is
limited and not a guaranteed complete historical or real-time source.
"""
import json,datetime as dt
from pathlib import Path
from omega_sec_event_watch import parse_atom,fetch_sec
from omega_catalyst_registry import route_sec_events,coverage
def checkpoint(feed,prior=None):
 now=dt.datetime.now(dt.timezone.utc).isoformat()
 entries=parse_atom(feed)
 if not entries:raise ValueError("empty SEC feed")
 seen=set((prior or {}).get("seen_ids",[]))
 new=[e for e in entries if e["id"] not in seen]
 ids=list(dict.fromkeys([e["id"] for e in entries]+list((prior or {}).get("seen_ids",[]))))[:5000]
 return {"checked_at":now,"status":"SEC_CURRENT_FEED_PARTIAL",
  "feed_entries":len(entries),"new_filings":len(new),
  "events":route_sec_events(new),"seen_ids":ids,
  "catalyst_coverage":coverage(),"trade_eligible":False}
def main():
 path=Path("state/omega_catalyst_feed.json")
 prior=json.loads(path.read_text()) if path.exists() else None
 try:r=checkpoint(fetch_sec(),prior)
 except Exception as e:
  r={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
    "status":"SOURCE_FAILED","error":type(e).__name__+":"+str(e)[:160],
    "seen_ids":(prior or {}).get("seen_ids",[]),
    "previous_successful_checkpoint":(prior or {}).get("checked_at"),
    "catalyst_coverage":coverage(),"trade_eligible":False}
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
 print(json.dumps({k:v for k,v in r.items() if k not in ("events","seen_ids","catalyst_coverage")},indent=2))
if __name__=="__main__":main()
