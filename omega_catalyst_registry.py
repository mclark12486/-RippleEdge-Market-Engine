"""Cross-market catalyst event classification and coverage contract.

This is an evidence-routing layer, not proof of full-market surveillance.
SEC filing forms identify event *candidates*; filing contents must be read
before confirming a transaction, lawsuit, management change, or catalyst.
"""
import datetime as dt,re
CATEGORIES={
 "mergers_acquisitions":{"sec_forms":["8-K","8-K/A","S-4","DEFM14A","SC TO-T","SC 13D"],"other_sources":["FTC","DOJ"],"status":"SEC_FORM_SCREEN_ONLY"},
 "legal_litigation":{"sec_forms":["8-K","10-K","10-Q"],"other_sources":["PACER","CourtListener","state_courts"],"status":"NOT_CONNECTED"},
 "management_hiring_firing":{"sec_forms":["8-K","8-K/A","DEF 14A"],"other_sources":["company_careers","job_boards"],"status":"SEC_FORM_SCREEN_ONLY"},
 "patents_ip":{"sec_forms":["10-K","8-K"],"other_sources":["USPTO","WIPO","EPO"],"status":"NOT_CONNECTED"},
 "research_developments":{"sec_forms":["8-K","10-Q"],"other_sources":["ClinicalTrials.gov","Europe_PMC","PubMed"],"status":"PARTIAL_NAME_SEARCH"},
 "government_contracts":{"sec_forms":["8-K"],"other_sources":["USAspending","SAM.gov"],"status":"PARTIAL_NAME_SEARCH"},
 "construction_permits":{"sec_forms":[],"other_sources":["Chicago_permits","NYC_permits"],"status":"TWO_MUNICIPAL_FEEDS_ONLY"},
 "earnings_guidance":{"sec_forms":["8-K","10-Q","10-K","6-K"],"other_sources":["issuer_ir"],"status":"SEC_FORM_SCREEN_ONLY"},
 "financing_capital":{"sec_forms":["8-K","S-3","424B5","SC 13G"],"other_sources":[],"status":"SEC_FORM_SCREEN_ONLY"},
}
def classify_sec(title):
 title=str(title)
 # SEC current feed titles begin with form (e.g. '8-K - Issuer ...').
 m=re.match(r"^\s*(8-K/A|8-K|10-K|10-Q|6-K|S-4|DEFM14A|SC TO-T|SC 13D|SC 13G|DEF 14A|S-3|424B5)\b",title,re.I)
 form=m.group(1).upper() if m else None
 return {"form":form,"candidate_categories":[k for k,v in CATEGORIES.items() if form in v["sec_forms"]],
  "status":"FORM_ONLY_UNVERIFIED","event_confirmed":False,"trade_eligible":False}
def route_sec_events(entries):
 return [{"source":"SEC_CURRENT_FILINGS","source_id":e["id"],
  "title":e["title"],"updated":e.get("updated"),
  **classify_sec(e["title"])} for e in entries]
def coverage():
 return {"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),
  "marketwide_all_categories_verified":False,"categories":CATEGORIES,
  "note":"No connector provides complete real-time coverage of every company or every event."}
