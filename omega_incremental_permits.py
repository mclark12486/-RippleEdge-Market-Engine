"""Incremental permit ingestion: read source pages once, then screen against SEC directory.

A page cursor is a traversal checkpoint, NOT a durable change-data-capture
watermark. Offset pagination may miss records inserted ahead of the cursor;
periodic full sweeps and provider-specific date-key watermarks are still needed.
"""
import argparse,csv,datetime as dt,hashlib,json,re,urllib.parse
from pathlib import Path
from omega_geographic_records import JURISDICTIONS,fetch_json,stable_id
from omega_entity_resolution import normalize
def page_url(cfg,offset,limit):
 if offset<0 or not 1<=limit<=100:raise ValueError("invalid pagination")
 q=urllib.parse.urlencode({"$limit":limit,"$offset":offset,"$order":":id ASC"})
 return "https://"+cfg["host"]+"/resource/"+cfg["dataset"]+".json?"+q
def directory(path):
 with open(path,newline="",encoding="utf-8") as f:rows=list(csv.DictReader(f))
 # Require multiword, sufficiently specific names to reduce false positives.
 index={}
 for row in rows:
  name=normalize(row.get("name",""))
  parts=name.split()
  if len(parts)<2 or len(name)<9:continue
  anchor=max(parts,key=len)
  if len(anchor)<5:continue
  index.setdefault(anchor,[]).append((name,row["symbol"],row.get("cik","")))
 return index
def mentions(record,index):
 content=normalize(" ".join(str(v) for v in record.values() if isinstance(v,(str,int,float))))
 tokens=set(content.split());hits=[];seen=set()
 for token in tokens:
  for name,symbol,cik in index.get(token,()):
   if (symbol,cik) in seen:continue
   if (" "+name+" ") in (" "+content+" "):
    seen.add((symbol,cik))
    hits.append({"symbol":symbol,"cik":cik,"matched_name":name,
     "status":"UNVERIFIED_NAME_MENTION","ownership_verified":False,
     "subsidiary_relationship_verified":False,"trade_eligible":False})
 return hits
def ingest(prior,index,jurisdictions=None,fetch=fetch_json,limit=25,seen_limit=30000):
 if not 1<=limit<=100:raise ValueError("limit")
 selected=jurisdictions or list(JURISDICTIONS)
 now=dt.datetime.now(dt.timezone.utc).isoformat()
 state={"checked_at":now,"sources":dict((prior or {}).get("sources",{})),
  "records_fetched_this_run":0,"new_records_this_run":0,
  "potential_company_mentions_this_run":0,"source_failures":0,
  "results":[],"trade_eligible":False,"marketwide_coverage":"NOT_ESTABLISHED"}
 for jurisdiction in selected:
  cfg=JURISDICTIONS[jurisdiction]
  old=state["sources"].get(jurisdiction,{})
  offset=int(old.get("offset",0))
  ids=list(old.get("recent_ids",[]))[-seen_limit:]
  known=set(ids)
  try:
   rows=fetch(page_url(cfg,offset,limit))
   if not isinstance(rows,list):raise ValueError("unexpected response")
   new=0
   for row in rows:
    if not isinstance(row,dict):continue
    uid=stable_id(jurisdiction,row)
    if uid in known:continue
    known.add(uid);ids.append(uid);new+=1
    hits=mentions(row,index)
    state["potential_company_mentions_this_run"]+=len(hits)
    if hits:state["results"].append({"id":uid,"jurisdiction":jurisdiction,
      "source":"https://"+cfg["host"]+"/resource/"+cfg["dataset"]+".json",
      "mentions":hits,"record":row,"trade_eligible":False})
   state["records_fetched_this_run"]+=len(rows)
   state["new_records_this_run"]+=new
   next_offset=offset+len(rows) if len(rows)==limit else 0
   state["sources"][jurisdiction]={"status":"PAGE_FETCH_OK","offset":next_offset,
    "pages_fetched":int(old.get("pages_fetched",0))+1,
    "rows_fetched":int(old.get("rows_fetched",0))+len(rows),
    "unique_records_seen_in_window":len(known),
    "recent_ids":ids[-seen_limit:],"last_success":now,
    "sweep_complete":len(rows)<limit,
    "completeness_verified":False}
  except Exception as e:
   state["source_failures"]+=1
   state["sources"][jurisdiction]={**old,"status":"PAGE_FETCH_FAILED",
    "error":type(e).__name__+":"+str(e)[:140],"last_failure":now}
 return state
def main():
 a=argparse.ArgumentParser()
 a.add_argument("--directory",default="state/omega_sec_company_directory.csv")
 a.add_argument("--state",default="state/omega_incremental_permits.json")
 a.add_argument("--limit",type=int,default=25)
 args=a.parse_args()
 path=Path(args.state);prior=json.loads(path.read_text()) if path.exists() else None
 result=ingest(prior,directory(args.directory),limit=args.limit)
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 print(json.dumps({k:v for k,v in result.items() if k not in ("sources","results")},indent=2))
 print(json.dumps({k:{z:v for z,v in s.items() if z!="recent_ids"} for k,s in result["sources"].items()},indent=2))
if __name__=="__main__":main()
