"""Municipal API health probe, independent of full-text company search."""
import json,datetime as dt
from pathlib import Path
from omega_geographic_records import JURISDICTIONS,health_url,fetch_json
def probe(fetch=fetch_json):
 result={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),"sources":{}}
 for name,c in JURISDICTIONS.items():
  try:
   rows=fetch(health_url(c))
   if not isinstance(rows,list):raise ValueError("unexpected response")
   result["sources"][name]={"status":"API_READ_OK","sample_rows":len(rows),
    "company_search_verified":False}
  except Exception as e:
   result["sources"][name]={"status":"API_READ_FAILED","error":type(e).__name__+":"+str(e)[:140],
    "company_search_verified":False}
 return result
if __name__=="__main__":
 r=probe();p=Path("state/omega_geographic_health.json");p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(r,indent=2)+"\n");print(json.dumps(r,indent=2))
