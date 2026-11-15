"""Independent SEC filing arrival watcher. No brokerage access.

This is periodic polling, NOT a continuous stream or complete coverage.
SEC may block/limit access; fail closed and report errors.
"""
import datetime as dt,hashlib,json,os,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
STATE=Path("state/omega_sec_event_watch.json")
URL="https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&output=atom&count=100"
NS={"a":"http://www.w3.org/2005/Atom"}
def parse_atom(data):
 root=ET.fromstring(data)
 if root.tag!="{http://www.w3.org/2005/Atom}feed":raise ValueError("unexpected SEC feed")
 out=[]
 for e in root.findall("a:entry",NS):
  uid=(e.findtext("a:id",default="",namespaces=NS) or "").strip()
  title=(e.findtext("a:title",default="",namespaces=NS) or "").strip()
  updated=(e.findtext("a:updated",default="",namespaces=NS) or "").strip()
  if uid and title and updated:out.append({"id":uid,"title":title,"updated":updated})
 return out
def check(fetch,prior=None,now=None):
 now=now or dt.datetime.now(dt.timezone.utc).isoformat()
 entries=parse_atom(fetch())
 if not entries:raise ValueError("empty feed: no completeness claim")
 old=set((prior or {}).get("seen_ids",[]))
 fresh=[x for x in entries if x["id"] not in old]
 seen=list(dict.fromkeys([x["id"] for x in entries]+list(old)))[:1000]
 return {"status":"POLL_SUCCESS_PARTIAL_FEED","checked_at":now,
  "feed_entries":len(entries),"new_entries":len(fresh),
  "events":fresh[:100],"seen_ids":seen,
  "limitations":"SEC current filings Atom feed only; not every filing, press release, patent, permit or market event. Polling can be delayed."}
def fetch_sec():
 agent=os.environ.get("SEC_USER_AGENT","")
 if not agent or "@" not in agent:raise ValueError("SEC_USER_AGENT required")
 req=urllib.request.Request(URL,headers={"User-Agent":agent,"Accept":"application/atom+xml"})
 with urllib.request.urlopen(req,timeout=20) as resp:return resp.read(2_000_000)
def main():
 prior=json.loads(STATE.read_text()) if STATE.exists() else None
 try:
  result=check(fetch_sec,prior)
 except Exception as e:
  print(json.dumps({"status":"POLL_BLOCKED","reason":str(e)[:180]}))
  raise SystemExit(2)
 STATE.parent.mkdir(parents=True,exist_ok=True)
 STATE.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print(json.dumps({k:v for k,v in result.items() if k not in ("seen_ids","events")},sort_keys=True))
if __name__=="__main__":main()
