"""No-agent cron, mid-afternoon ET: flatten any SPY paper position with a market-on-close sell; log the open fill."""
import datetime as dt
from common import FILLS, NY, append, alpaca
ap = alpaca(); day = dt.datetime.now(NY).date().isoformat()
try: o = ap(f"/v2/orders:by_client_order_id?client_order_id=e16b-open-{day}")
except Exception: o = None
if o: append(FILLS, {"date": day, "event": "open_fill", "status": o.get("status"), "filled_avg_price": o.get("filled_avg_price"), "qty": o.get("filled_qty")})
try: pos = ap("/v2/positions/SPY")
except Exception: pos = None
if pos and float(pos["qty"]) > 0:
    s = ap("/v2/orders", {"symbol": "SPY", "qty": pos["qty"], "side": "sell", "type": "market", "time_in_force": "cls", "client_order_id": f"e16b-close-{day}"})
    append(FILLS, {"date": day, "event": "close_order", "status": s.get("status"), "qty": pos["qty"]}); print("MOC sell", pos["qty"], s.get("status"))
else: print("flat; nothing to close")
