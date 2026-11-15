"""Provider snapshot census for historical completeness checks.

Counts and endpoint responsiveness are evidence, not proof of immutable
snapshots. Snapshot consistency must be established by provider capabilities.
"""
import datetime as dt,json,urllib.parse
from pathlib import Path
from omega_geographic_records import JURISDICTIONS,fetch_json
def count_url(cfg):
 q=urllib.parse.urlencode({"$select":"count(*)"})
 return "https://"+cfg["host"]+"/resource/"+cfg["dataset"]+".json?"+q
def census(fetch=fetch_json):
 now=dt.datetime.now(dt.timezone.utc).isoformat()
 report={"checked_at":now,"sources":{},"historical_completeness_verified":False}
 for name,cfg in JURISDICTIONS.items():
  try:
   rows=fetch(count_url(cfg))
   if not isinstance(rows,list) or len(rows)!=1:raise ValueError("invalid count response")
   value=next((v for k,v in rows[0].items() if k in ("count","count_1","count_*")),None)
   if value is None:raise ValueError("count field missing")
   count=int(value)
   if count<0:raise ValueError("negative count")
   report["sources"][name]={"status":"COUNT_OK","reported_rows":count,
    "snapshot_consistent":False,"historical_completeness_verified":False}
  except Exception as e:
   report["sources"][name]={"status":"COUNT_FAILED","error":type(e).__name__+":"+str(e)[:160],
    "historical_completeness_verified":False}
 return report
if __name__=="__main__":
 r=census();p=Path("state/omega_permit_source_counts.json")
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,indent=2)+"\n")
 print(json.dumps(r,indent=2))
