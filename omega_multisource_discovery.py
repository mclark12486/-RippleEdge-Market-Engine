"""Omega multi-source public-event discovery.

Coverage is explicitly partial. Each connector is independently fail-closed.
Public source search is not proof that an event affects a traded company.
"""
import datetime as dt,json,os,urllib.parse,urllib.request
from pathlib import Path
BASE={
 "clinical_trials":"https://clinicaltrials.gov/api/v2/studies",
 "federal_register":"https://www.federalregister.gov/api/v1/documents.json",
 "research":"https://www.ebi.ac.uk/europepmc/webservices/rest/search",
 "federal_awards":"https://api.usaspending.gov/api/v2/search/spending_by_award/",
}
def fetch_json(url,*,payload=None,timeout=18):
 data=None if payload is None else json.dumps(payload).encode()
 headers={"User-Agent":os.environ.get("OMEGA_USER_AGENT","RippleEdge-Omega/0.1 research contact unknown"),"Accept":"application/json"}
 if data is not None:headers["Content-Type"]="application/json"
 req=urllib.request.Request(url,data=data,headers=headers)
 with urllib.request.urlopen(req,timeout=timeout) as resp:return json.load(resp)
def scan_company(name,fetch=fetch_json):
 if not isinstance(name,str) or len(name.strip())<3:raise ValueError("company name required")
 q=name.strip();out={"company_query":q,"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
  "sources":{},"events":[],"coverage":"PARTIAL_PUBLIC_SOURCES_NOT_FULL_MARKET"}
 tasks=[
 ("clinical_trials",BASE["clinical_trials"]+"?"+urllib.parse.urlencode({"query.term":q,"pageSize":20,"format":"json"}),None),
 ("federal_register",BASE["federal_register"]+"?"+urllib.parse.urlencode({"conditions[term]":q,"per_page":20}),None),
 ("research",BASE["research"]+"?"+urllib.parse.urlencode({"query":q,"format":"json","pageSize":20}),None),
 ("federal_awards",BASE["federal_awards"],{"filters":{"keywords":[q],"award_type_codes":["A","B","C","D"]},"fields":["Award ID","Recipient Name","Award Amount","Description","Awarding Agency"],"page":1,"limit":20,"sort":"Award Amount","order":"desc","subawards":False}),
 ]
 for source,url,payload in tasks:
  try:
   data=fetch(url,payload=payload)
   if source=="clinical_trials":
    items=data.get("studies",[])
    rows=[{"id":x.get("protocolSection",{}).get("identificationModule",{}).get("nctId"),
           "title":x.get("protocolSection",{}).get("identificationModule",{}).get("briefTitle"),
           "updated":x.get("protocolSection",{}).get("statusModule",{}).get("studyFirstPostDateStruct",{}).get("date")}
          for x in items]
   elif source=="federal_register":
    rows=[{"id":x.get("document_number"),"title":x.get("title"),"updated":x.get("publication_date"),"url":x.get("html_url")} for x in data.get("results",[])]
   elif source=="research":
    rows=[{"id":x.get("id"),"title":x.get("title"),"updated":x.get("firstPublicationDate"),"doi":x.get("doi")} for x in data.get("resultList",{}).get("result",[])]
   else:
    rows=[{"id":x.get("Award ID"),"title":x.get("Description"),"recipient":x.get("Recipient Name"),"amount":x.get("Award Amount")} for x in data.get("results",[])]
   rows=[dict(x,source=source,relationship="UNVERIFIED_NAME_SEARCH") for x in rows if x.get("id")]
   out["sources"][source]={"status":"SEARCH_OK_NOT_ENTITY_VERIFIED","results":len(rows)}
   out["events"].extend(rows)
  except Exception as e:
   out["sources"][source]={"status":"BLOCKED","error":type(e).__name__+":"+str(e)[:120]}
 out["status"]="PARTIAL" if any(x["status"]=="BLOCKED" for x in out["sources"].values()) else "SEARCH_COMPLETE_ENTITY_UNVERIFIED"
 return out
def main():
 import argparse
 a=argparse.ArgumentParser();a.add_argument("--company",required=True);a.add_argument("--output",default="state/omega_multisource_latest.json")
 args=a.parse_args();r=scan_company(args.company)
 path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
 print(json.dumps({"status":r["status"],"company":args.company,"sources":r["sources"],"events":len(r["events"])},indent=2))
if __name__=="__main__":main()
