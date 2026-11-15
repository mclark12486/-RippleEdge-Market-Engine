"""Rotating company x jurisdiction public-record scanner with persistent cursor.

Explicitly reports configured and attempted coverage; never claims full market.
Does not promote name matches into verified corporate relationships or trades.
"""
import argparse,csv,datetime as dt,json
from pathlib import Path
from omega_geographic_records import JURISDICTIONS,scan,health_url,fetch_json
from omega_entity_resolution import enrich
def load_universe(path):
 with open(path,newline="",encoding="utf-8") as f:rows=list(csv.DictReader(f))
 companies=[{"symbol":(r.get("symbol") or "").strip().upper(),
             "name":(r.get("name") or "").strip()} for r in rows]
 companies=[x for x in companies if x["symbol"] and len(x["name"])>=3]
 if not companies or len(set(x["symbol"] for x in companies))!=len(companies):
  raise ValueError("empty or duplicate universe")
 return companies
def checkpoint(companies,jurisdictions=None,prior=None,batch_size=4,scanner=scan):
 jurisdictions=jurisdictions or list(JURISDICTIONS)
 if not companies or not jurisdictions or not 1<=batch_size<=30:raise ValueError("invalid census")
 if any(j not in JURISDICTIONS for j in jurisdictions):raise ValueError("unsupported jurisdiction")
 total=len(companies)*len(jurisdictions)
 start=int((prior or {}).get("cursor",0))%total
 tasks=[]
 for i in range(min(batch_size,total)):
  idx=(start+i)%total
  company=companies[idx//len(jurisdictions)]
  jurisdiction=jurisdictions[idx%len(jurisdictions)]
  tasks.append((company,jurisdiction))
 results=[];ok=0;failed=0;skipped=0;blocked_sources=set()
 for company,jurisdiction in tasks:
  if jurisdiction in blocked_sources:
   skipped+=1
   results.append({"symbol":company["symbol"],"jurisdiction":jurisdiction,
    "status":"SKIPPED_SOURCE_CIRCUIT_OPEN","trade_eligible":False})
   continue
  try:
   r=scanner(company["name"],[jurisdiction])
   source=r["jurisdictions"][jurisdiction]
   if source["status"]=="BLOCKED":
    failed+=1
    blocked_sources.add(jurisdiction)
   else:ok+=1
   records=enrich(r["records"],{company["symbol"]:[company["name"]]})
   results.append({"symbol":company["symbol"],"company":company["name"],
     "jurisdiction":jurisdiction,"status":source["status"],"source":source,
     "records":records[:30],"trade_eligible":False})
  except Exception as e:
   failed+=1
   blocked_sources.add(jurisdiction)
   results.append({"symbol":company["symbol"],"jurisdiction":jurisdiction,
    "status":"BLOCKED","error":type(e).__name__+":"+str(e)[:150]})
 seen=dict((prior or {}).get("last_attempt_by_pair",{}))
 succeeded=dict((prior or {}).get("last_success_by_pair",{}))
 now=dt.datetime.now(dt.timezone.utc).isoformat()
 for item in results:
  if item["status"]=="SKIPPED_SOURCE_CIRCUIT_OPEN":continue
  key=item["symbol"]+"|"+item["jurisdiction"]
  seen[key]=now
  if item["status"]!="BLOCKED":succeeded[key]=now
 return {"checked_at":now,"configured_companies":len(companies),
  "configured_jurisdictions":len(jurisdictions),"configured_pairs":total,
  "attempted_pairs_this_run":len(tasks),"successful_queries_this_run":ok,
  "failed_queries_this_run":failed,"skipped_circuit_open_this_run":skipped,
  "successful_pairs_ever":len(succeeded),
  "configured_pair_success_coverage":len(succeeded)/total,
  "last_success_by_pair":succeeded,"cursor":(start+len(tasks))%total,
  "unique_pairs_attempted":len(seen),"configured_pair_attempt_coverage":len(seen)/total,
  "last_attempt_by_pair":seen,"results":results,
  "failed_or_skipped_pairs_to_retry":[x["symbol"]+"|"+x["jurisdiction"] for x in results if x["status"] in ("BLOCKED","SKIPPED_SOURCE_CIRCUIT_OPEN")],
  "marketwide_coverage":"NOT_ESTABLISHED","all_us_jurisdictions_coverage":"NOT_ESTABLISHED",
  "company_relationships_verified":0,"trade_eligible":False}
def main():
 a=argparse.ArgumentParser()
 a.add_argument("--universe",default="state/omega_sec_company_directory.csv")
 a.add_argument("--state",default="state/omega_geographic_census.json")
 a.add_argument("--batch-size",type=int,default=4)
 args=a.parse_args()
 path=Path(args.state)
 prior=json.loads(path.read_text()) if path.exists() else None
 result=checkpoint(load_universe(args.universe),prior=prior,batch_size=args.batch_size)
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 print(json.dumps({k:result[k] for k in ("configured_companies","configured_jurisdictions",
  "configured_pairs","attempted_pairs_this_run","successful_queries_this_run",
  "failed_queries_this_run","unique_pairs_attempted","configured_pair_attempt_coverage","cursor")},indent=2))
if __name__=="__main__":main()
