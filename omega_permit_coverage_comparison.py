"""Compare provider totals with conservative ingested unique-record lower bounds."""
import json,datetime as dt
from pathlib import Path
def compare(ingestion,counts):
 result={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
  "sources":{},"historical_completeness_verified":False}
 for name,source in counts.get("sources",{}).items():
  local=ingestion.get("sources",{}).get(name,{})
  total=source.get("reported_rows") if source.get("status")=="COUNT_OK" else None
  unique=int(local.get("cumulative_unique_records_lower_bound",local.get("unique_records_seen_in_window",0)))
  result["sources"][name]={"provider_rows":total,
   "ingested_unique_lower_bound":unique,
   "observed_fraction_lower_bound":round(unique/total,8) if isinstance(total,int) and total>0 else None,
   "provider_count_verified":total is not None,
   "unique_count_is_exact":False,"historical_completeness_verified":False,
   "reason":"Sliding dedup window and changing provider data prevent exact full-history proof"}
 return result
if __name__=="__main__":
 a=json.loads(Path("state/omega_incremental_permits.json").read_text())
 b=json.loads(Path("state/omega_permit_source_counts.json").read_text())
 r=compare(a,b);p=Path("state/omega_permit_coverage_comparison.json")
 p.write_text(json.dumps(r,indent=2)+"\n");print(json.dumps(r,indent=2))
