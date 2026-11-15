"""Provider schema inspection; field names must be validated, never assumed."""
import datetime as dt,json
from pathlib import Path
from omega_geographic_records import JURISDICTIONS,health_url,fetch_json
CANDIDATE_TERMS=("updated","modified","last_change","last_update","issued","issue_date","filing_date","created")
def inspect(fetch=fetch_json):
 report={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),"sources":{}}
 for name,cfg in JURISDICTIONS.items():
  try:
   rows=fetch(health_url(cfg))
   if not isinstance(rows,list) or not rows or not isinstance(rows[0],dict):
    raise ValueError("missing sample record")
   fields=list(rows[0])
   candidates=[k for k in fields if any(t in k.lower() for t in CANDIDATE_TERMS)]
   report["sources"][name]={"status":"SAMPLE_SCHEMA_READ_OK",
    "fields":fields,"candidate_timestamp_fields":candidates,
    "provider_update_field_validated":False,
    "note":"Field presence alone does not prove update semantics or monotonicity"}
  except Exception as e:
   report["sources"][name]={"status":"SAMPLE_SCHEMA_READ_FAILED",
    "error":type(e).__name__+":"+str(e)[:140],"provider_update_field_validated":False}
 return report
if __name__=="__main__":
 r=inspect();p=Path("state/omega_permit_schema_inspection.json")
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,indent=2)+"\n")
 print(json.dumps(r,indent=2))
