"""Omega point-in-time replay foundation. No external or future-data lookups.

Inputs MUST be genuine point-in-time snapshots; this module cannot authenticate
a vendor's historical revisions, survivorship, or publication timestamps.
"""
from datetime import datetime, timezone
import hashlib
import json
import math

def _stamp(value):
 if not isinstance(value,str):raise ValueError("timestamp must be ISO-8601")
 t=datetime.fromisoformat(value.replace("Z","+00:00"))
 if t.tzinfo is None:raise ValueError("timezone required")
 return t.astimezone(timezone.utc)

def snapshot_at(records, decision_at):
 """Return only eligible records actually observed by the decision instant."""
 cutoff=_stamp(decision_at)
 out=[]
 for row in records:
  for field in ("symbol","published_at","ingested_at","source_id","value"):
   if field not in row:raise ValueError("missing "+field)
  if _stamp(row["published_at"])<=cutoff and _stamp(row["ingested_at"])<=cutoff:
   out.append(dict(row))
 return sorted(out,key=lambda r:(r["symbol"],r["published_at"],r["source_id"]))

def freeze_decision(records,decision_at,ranker,model_version):
 """Freeze deterministic decisions and the exact admissible evidence."""
 if not model_version:raise ValueError("model version required")
 evidence=snapshot_at(records,decision_at)
 if not evidence:raise ValueError("no point-in-time evidence")
 selections=ranker(tuple(dict(x) for x in evidence))
 if not isinstance(selections,(list,tuple)):raise ValueError("ranker must return a list")
 available={x["symbol"] for x in evidence}
 if len(set(selections))!=len(selections) or any(x not in available for x in selections):
  raise ValueError("selection outside admissible universe")
 payload={"decision_at":decision_at,"model_version":model_version,
          "evidence":evidence,"selected_symbols":list(selections),
          "execution":"NEXT_SESSION_ONLY_NOT_FILLED",
          "status":"RESEARCH_REPLAY_NOT_VALIDATED"}
 raw=json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)
 payload["sha256"]=hashlib.sha256(raw.encode()).hexdigest()
 return payload

def next_session_return(decision, bars, symbol, cost_bps=20):
 """Illustrative next-session OPEN to later CLOSE; never same-day fills."""
 cutoff=_stamp(decision["decision_at"])
 if symbol not in decision["selected_symbols"]:raise ValueError("unselected symbol")
 if not isinstance(cost_bps,(int,float)) or not math.isfinite(cost_bps) or cost_bps<0:raise ValueError("invalid costs")
 eligible=[]
 for bar in bars:
  if bar.get("symbol")!=symbol:continue
  if not bar.get("session_open_at") or not bar.get("session_close_at"):raise ValueError("bar timestamps required")
  opened=_stamp(bar["session_open_at"]);closed=_stamp(bar["session_close_at"])
  if opened>cutoff and closed>opened:eligible.append((opened,bar))
 eligible.sort(key=lambda x:x[0])
 if not eligible:return {"status":"MISSING_FUTURE_BARS","return":None}
 entry=eligible[0][1]
 if len(eligible)<2:return {"status":"PENDING_EXIT_BAR","return":None}
 exit_bar=eligible[1][1]
 price=float(entry["open"]);close=float(exit_bar["close"])
 if not all(math.isfinite(x) and x>0 for x in (price,close)):raise ValueError("invalid prices")
 return {"status":"ILLUSTRATIVE_NOT_EXECUTED","symbol":symbol,
         "entry_session":entry["session_open_at"],"exit_session":exit_bar["session_close_at"],
         "gross_return":close/price-1,"net_return":close/price-1-cost_bps/10000,
         "warning":"Requires authenticated point-in-time bars, corporate actions, delisted securities, spread and fill modeling"}
