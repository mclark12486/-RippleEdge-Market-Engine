"""Bounded rotating company-intelligence census.

Runs a small explicit batch per checkpoint. Tracks which symbols were checked,
which sources failed and how much of the requested universe was covered.
Not a complete market-wide company forensic audit.
"""
import argparse,csv,datetime as dt,json
from pathlib import Path
from omega_multisource_discovery import scan_company
from omega_evidence_graph import build_graph,rank_for_review
def census(companies,prior=None,batch_size=3,scanner=scan_company):
 if not 1<=batch_size<=20:raise ValueError("batch size")
 if not companies:raise ValueError("empty universe")
 if len(set(x["symbol"] for x in companies))!=len(companies):raise ValueError("duplicate symbol")
 prior=prior or {};start=int(prior.get("cursor",0))%len(companies)
 batch=[companies[(start+i)%len(companies)] for i in range(min(batch_size,len(companies)))]
 records=[];checked=[]
 for x in batch:
  symbol=x["symbol"];name=x["name"]
  try:
   found=scanner(name)
   graph=build_graph(name,found.get("events",[]))
   records.append({"symbol":symbol,"name":name,"status":found["status"],
     "sources":found["sources"],"graph":graph,"research_queue":rank_for_review(graph)[:15]})
   checked.append(symbol)
  except Exception as e:
   records.append({"symbol":symbol,"name":name,"status":"BLOCKED",
     "error":type(e).__name__+":"+str(e)[:140]})
 return {"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
  "universe_size":len(companies),"batch_attempted":len(batch),"batch_checked":len(checked),
  "batch_coverage":len(checked)/len(companies),"cursor":(start+len(batch))%len(companies),
  "records":records,"trade_eligible":False,
  "limitations":"Rotating name-based search, not full-universe real-time or verified corporate linkage"}
def load_companies(path):
 with open(path,newline="",encoding="utf-8") as f:
  rows=list(csv.DictReader(f))
 result=[]
 for row in rows:
  sym=(row.get("symbol") or "").strip().upper();name=(row.get("name") or "").strip()
  if sym and len(name)>=3:result.append({"symbol":sym,"name":name})
 return result
def main():
 a=argparse.ArgumentParser()
 a.add_argument("--universe",default="omega_company_universe.csv")
 a.add_argument("--state",default="state/omega_company_census.json")
 a.add_argument("--batch-size",type=int,default=3)
 args=a.parse_args();path=Path(args.state)
 prior=json.loads(path.read_text()) if path.exists() else {}
 result=census(load_companies(args.universe),prior,args.batch_size)
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 print(json.dumps({"universe_size":result["universe_size"],"batch_attempted":result["batch_attempted"],
  "batch_checked":result["batch_checked"],"cursor":result["cursor"]}))
if __name__=="__main__":main()
