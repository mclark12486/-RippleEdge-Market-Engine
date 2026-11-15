"""Conservative company/subsidiary name matching for geographic records.

Alias matching is a research lead only; never confirms beneficial ownership,
contract value, project financing or equity catalyst.
"""
import re
def normalize(s):
 return " ".join(re.findall(r"[a-z0-9]+",str(s).casefold()))
def matches(record,aliases):
 if not isinstance(record,dict):return []
 corpus=normalize(" ".join(str(v) for v in record.values() if isinstance(v,(str,int,float))))
 found=[]
 for alias in aliases:
  name=normalize(alias)
  if len(name)<5 or len(name.split())<2:continue
  if (" "+name+" ") in (" "+corpus+" "):
   found.append({"alias":alias,"status":"POTENTIAL_NAME_MENTION_ONLY",
                 "entity_verified":False,"ownership_verified":False,
                 "project_financial_materiality_verified":False})
 return found
def enrich(records,company_aliases):
 result=[]
 for row in records:
  x=dict(row)
  x["potential_mentions"]=[]
  for ticker,aliases in company_aliases.items():
   for hit in matches(row.get("record",{}),aliases):
    x["potential_mentions"].append({"ticker":ticker,**hit})
  x["trade_eligible"]=False
  result.append(x)
 return result
