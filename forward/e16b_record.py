"""Record today's pre-open calls (append-only) and, for e16b LONG, place the Alpaca PAPER market-on-open buy.
usage: python e16b_record.py --spy LONG|FLAT --p 0.0-1.0 --pick TICKER|NONE --why "one line" """
import argparse, datetime as dt, sys
from common import CALLS, FILLS, NY, E17_UNIVERSE, append, rows, alpaca
QTY = 15
a = argparse.ArgumentParser(); a.add_argument("--spy", required=True, choices=["LONG", "FLAT"]); a.add_argument("--p", type=float, required=True)
a.add_argument("--pick", required=True, choices=E17_UNIVERSE + ["NONE"]); a.add_argument("--why", default=""); a.add_argument("--model", default="unknown")
x = a.parse_args(); now = dt.datetime.now(NY); day = now.date().isoformat()
if not 0 <= x.p <= 1: sys.exit("p out of range")
if (now.hour, now.minute) >= (9, 25): sys.exit(f"REFUSED: {now:%H:%M} ET is past the 09:25 deadline; no call recorded")
if any(r["date"] == day for r in rows(CALLS)): sys.exit(f"REFUSED: a call for {day} already exists (append-only, one per day)")
ap = alpaca(); cal = ap(f"/v2/calendar?start={day}&end={day}")
if not cal or cal[0]["date"] != day: sys.exit(f"market closed {day}; nothing recorded")
rec = {"date": day, "ts_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "e16b_spy": x.spy, "p_up": x.p,
       "e17_pick": x.pick, "why": x.why[:300], "model": x.model}
append(CALLS, rec); print("recorded", rec)
if x.spy == "LONG":
    o = ap("/v2/orders", {"symbol": "SPY", "qty": str(QTY), "side": "buy", "type": "market", "time_in_force": "opg", "client_order_id": f"e16b-open-{day}"})
    append(FILLS, {"date": day, "event": "open_order", "id": o.get("id"), "status": o.get("status")}); print("paper OPG buy", QTY, "SPY:", o.get("status"))
