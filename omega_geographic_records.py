"""Jurisdiction-specific public construction permit discovery.

Socrata catalog-backed adapters. Data availability, licensing and update
frequency vary by jurisdiction. A permit search hit is NOT a verified
relationship to any stock, parent company or subsidiary.
"""
import datetime as dt,hashlib,json,urllib.parse,urllib.request,urllib.error,os,time,random
from pathlib import Path
JURISDICTIONS={
 "chicago_building_permits":{"city":"Chicago","state":"IL","type":"building_permits",
  "host":"data.cityofchicago.org","dataset":"ydr8-5enu"},
 "nyc_dob_permits":{"city":"New York City","state":"NY","type":"building_permits",
  "host":"data.cityofnewyork.us","dataset":"ipu4-2q9a"},
}
def stable_id(jurisdiction,row):
 fields=["id","permit_","permit_number","permit_number_","job__","job_number","application_number"]
 primary=next((str(row[k]) for k in fields if row.get(k) is not None),None)
 if primary:return hashlib.sha256((jurisdiction+"|"+primary).encode()).hexdigest()[:24]
 raw=json.dumps(row,sort_keys=True,default=str)
 return hashlib.sha256((jurisdiction+"|"+raw).encode()).hexdigest()[:24]
def socrata_url(config,query,limit=20):
 if not 1<=limit<=100:raise ValueError("limit")
 if not 3<=len(query.strip())<=100:raise ValueError("query")
 params=urllib.parse.urlencode({"$q":query.strip(),"$limit":limit,"$select":"*"})
 return "https://"+config["host"]+"/resource/"+config["dataset"]+".json?"+params
def health_url(config):
 return "https://"+config["host"]+"/resource/"+config["dataset"]+".json?"+urllib.parse.urlencode({"$select":"count(*)","$limit":1})
def fetch_json(url):
 req=urllib.request.Request(url,headers={"User-Agent":"RippleEdgeOmega/0.1 public research","Accept":"application/json"})
 timeout=float(os.environ.get("OMEGA_GEO_HTTP_TIMEOUT","7"))
 attempts=int(os.environ.get("OMEGA_GEO_HTTP_ATTEMPTS","2"))
 if not 1<=attempts<=3:raise ValueError("invalid retry count")
 last=None
 for i in range(attempts):
  try:
   with urllib.request.urlopen(req,timeout=timeout) as resp:return json.load(resp)
  except (TimeoutError,urllib.error.URLError,urllib.error.HTTPError) as e:
   last=e
   if isinstance(e,urllib.error.HTTPError) and e.code not in (429,500,502,503,504):raise
   if i+1<attempts:time.sleep(min(1.5,0.4*(i+1)+random.random()*0.2))
 raise last
def scan(query,jurisdictions=None,fetch=fetch_json):
 selected=jurisdictions or list(JURISDICTIONS)
 report={"query":query,"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
  "jurisdictions":{},"records":[],"verified_company_links":0,
  "coverage":"ONLY_CONFIGURED_JURISDICTIONS_AND_SEARCH_RESULTS","trade_eligible":False}
 seen=set()
 for name in selected:
  if name not in JURISDICTIONS:raise ValueError("unknown jurisdiction "+name)
  config=JURISDICTIONS[name]
  try:
   rows=fetch(socrata_url(config,query))
   if not isinstance(rows,list):raise ValueError("unexpected dataset response")
   added=0
   for row in rows:
    if not isinstance(row,dict):continue
    uid=stable_id(name,row)
    if uid in seen:continue
    seen.add(uid);added+=1
    report["records"].append({"id":uid,"jurisdiction":name,
      "city":config["city"],"state":config["state"],
      "source_url":"https://"+config["host"]+"/resource/"+config["dataset"]+".json",
      "record":row,"company_relationship":"UNVERIFIED_NAME_SEARCH",
      "materiality":"NOT_ASSESSED","trade_eligible":False})
   report["jurisdictions"][name]={"status":"SEARCH_OK_NOT_COMPLETENESS_VERIFIED","records":added}
  except Exception as e:
   report["jurisdictions"][name]={"status":"BLOCKED","error":type(e).__name__+":"+str(e)[:140]}
 report["status"]="PARTIAL" if any(v["status"]=="BLOCKED" for v in report["jurisdictions"].values()) else "SEARCH_COMPLETE_RELATIONSHIPS_UNVERIFIED"
 return report
def main():
 import argparse
 a=argparse.ArgumentParser();a.add_argument("--query",required=True)
 a.add_argument("--output",default="state/omega_geographic_latest.json")
 args=a.parse_args();result=scan(args.query)
 dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 print(json.dumps({"status":result["status"],"jurisdictions":result["jurisdictions"],"records":len(result["records"])},indent=2))
if __name__=="__main__":main()
