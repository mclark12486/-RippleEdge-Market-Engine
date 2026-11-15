"""RippleEdge public-evidence relationship graph, strictly unverified by default.

A search match is NOT a confirmed corporate relationship. Graph stores
provenance and never promotes a search hit into a trade signal.
"""
import hashlib,json,re
def key(kind,name):
 return hashlib.sha256((kind+"|"+name.casefold().strip()).encode()).hexdigest()[:20]
def build_graph(company,events):
 if not company or not isinstance(events,list):raise ValueError("invalid graph input")
 root=key("company",company)
 nodes={root:{"id":root,"type":"company_query","name":company,"verification":"UNVERIFIED"}}
 edges=[]
 for event in events:
  if not isinstance(event,dict):continue
  source=event.get("source");eid=event.get("id")
  if not source or not eid:continue
  identity=str(source)+":"+str(eid)
  node_id=key("source_record",identity)
  nodes[node_id]={"id":node_id,"type":"source_record","source":source,
   "source_id":str(eid),"title":str(event.get("title") or "")[:500],
   "updated":event.get("updated"),"verification":"UNVERIFIED_NAME_SEARCH",
   "url":event.get("url"),"doi":event.get("doi")}
  edges.append({"from":root,"to":node_id,"relation":"SEARCH_RESULT_POSSIBLY_RELEVANT",
                "confidence":"UNVERIFIED","evidence_source":source})
 return {"schema_version":1,"company_query":company,"nodes":list(nodes.values()),
  "edges":edges,"verified_company_relationships":0,
  "trade_eligible":False,
  "warning":"No evidence of ownership, contract, subsidiary, causality or materiality established"}
def rank_for_review(graph):
 # Ranking means human research priority, never buy recommendation.
 priority={"clinical_trials":4,"federal_awards":3,"federal_register":2,"research":1}
 return sorted(({"source":n["source"],"source_id":n["source_id"],"title":n["title"],
  "priority":priority.get(n["source"],0),"status":"NEEDS_ENTITY_AND_MATERIALITY_VERIFICATION"}
  for n in graph["nodes"] if n["type"]=="source_record"),
  key=lambda x:(-x["priority"],x["source_id"]))
