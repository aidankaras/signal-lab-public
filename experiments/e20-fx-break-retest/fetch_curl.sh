#!/bin/bash
# Fallback cache filler: download Dukascopy monthly hourly-candle files with curl
# into $E20_HOME/cache (default: this folder). Useful when the Python fetcher
# times out from a given network. Months the feed lacks get an empty marker
# file, which fetch_dukascopy.py treats as "missing" instead of retrying.
# Then run: python fetch_dukascopy.py && python run_e20.py out
set -u
H=${E20_HOME:-$(cd "$(dirname "$0")" && pwd)}; C=$H/cache; mkdir -p "$C"
PAIRS="EURUSD GBPUSD USDJPY USDCHF USDCAD AUDUSD NZDUSD GBPJPY GBPCHF AUDCAD"
END_Y=${END_Y:-2026}; END_M=${END_M:-10}
for p in $PAIRS; do for y in $(seq 2015 "$END_Y"); do for m in $(seq 1 12); do
  [ "$y" -eq "$END_Y" ] && [ "$m" -gt "$END_M" ] && continue
  f=$(printf "%s_%d_%02d.bi5" "$p" "$y" "$m")
  [ -e "$C/$f" ] && continue
  code=000
  for a in 1 2 3 4 5; do   # Dukascopy months are 0-indexed in the URL
    code=$(curl -s -o "$C/$f" -w "%{http_code}" --max-time 60 -A Mozilla/5.0 \
      "https://datafeed.dukascopy.com/datafeed/$p/$y/$(printf %02d $((m-1)))/BID_candles_hour_1.bi5")
    [ "$code" = 200 ] && [ -s "$C/$f" ] && break
    rm -f "$C/$f"; [ "$code" = 404 ] && break; sleep $((5*a))
  done
  [ -s "$C/$f" ] || : > "$C/$f"
  echo "$f $code"; sleep 1.5
done; done; done
