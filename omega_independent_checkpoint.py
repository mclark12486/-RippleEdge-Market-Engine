"""Independent scheduled Omega shadow checkpoint, no broker integration.

Market observations are research-only Yahoo adjusted closes. The initial
policy is cash-only until an independently verified alpha signal exists.
State is stored in a dedicated JSON file and advanced at most once/session.
"""
import datetime as dt,json,os
from pathlib import Path
from omega_paper_engine import initial,step
from omega_performance_audit import metrics
STATE=Path("state/omega_independent_paper_state.json")
RECEIPT=Path("state/omega_independent_paper_latest.json")
def checkpoint(fetcher,state_path=STATE,receipt_path=RECEIPT):
 raw=fetcher()
 if not raw or any(k not in raw for k in ("session","prices","spy_return")):
  return {"status":"DATA_BLOCKED","reason":"MISSING_MARKET_DATA"}
 session=raw["session"]
 if not isinstance(session,str) or len(session)!=10:return {"status":"DATA_BLOCKED","reason":"BAD_SESSION"}
 if not isinstance(raw["prices"],dict) or "SPY" not in raw["prices"]:
  return {"status":"DATA_BLOCKED","reason":"NO_SPY_PRICE"}
 state=json.loads(state_path.read_text()) if state_path.exists() else initial()
 if state["last_session"] and session<=state["last_session"]:
  return {"status":"NO_NEW_SESSION","last_session":state["last_session"]}
 # No generated buy signals: evidence verification and point-in-time
 # forecast linkage have not passed acceptance tests.
 state=step(state,session,raw["prices"],[],market_return=raw["spy_return"])
 receipt={"status":"SHADOW_CASH_ONLY","session":session,
          "equity":state["equity"],"cash":state["cash"],
          "positions":state["positions"],"last_decision":state["ledger"][-1],
          "limitation":"No verified alpha, no intraday execution, no brokerage access"}
 state_path.parent.mkdir(parents=True,exist_ok=True)
 receipt_path.parent.mkdir(parents=True,exist_ok=True)
 state_path.write_text(json.dumps(state,sort_keys=True,indent=2)+"\n")
 receipt_path.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
 return receipt
def yahoo_observation():
 import yfinance as yf
 df=yf.download("SPY",period="10d",auto_adjust=True,progress=False,threads=False)
 if df is None or len(df)<2:raise ValueError("insufficient SPY history")
 cl=df["Close"]
 if hasattr(cl,"columns"):cl=cl.iloc[:,0]
 session=df.index[-1].date().isoformat()
 return {"session":session,"prices":{"SPY":float(cl.iloc[-1])},
         "spy_return":float(cl.iloc[-1]/cl.iloc[-2]-1)}
def main():
 try:r=checkpoint(yahoo_observation)
 except Exception as e:r={"status":"DATA_BLOCKED","reason":type(e).__name__+":"+str(e)[:180]}
 print(json.dumps(r,indent=2,sort_keys=True))
 if r["status"]=="DATA_BLOCKED":raise SystemExit(2)
if __name__=="__main__":main()
