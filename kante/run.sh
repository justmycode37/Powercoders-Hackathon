#!/usr/bin/env bash
# One entry point for the prototype.
#
#   ./run.sh              build everything that is missing, then serve on :8080
#   ./run.sh build        (re)build the data caches   [extra args go to `kante build`]
#   ./run.sh serve        serve only                  [extra args go to `kante serve`]
#   ./run.sh app          rebuild the web app only
#   ./run.sh phone        expose the running server to your tailnet over HTTPS
#
# Real-time data: put your opentransportdata.swiss API key in the environment
# variable KANTE_OTD_KEY, or keys per API in data/secrets/otd.json, before `serve`.
set -euo pipefail
cd "$(dirname "$0")"

PORT=${KANTE_PORT:-8080}
BIN=engine/target/release/kante

engine() { (cd engine && cargo build --release -p kante-server 2>&1 | tail -3); }
app() { (cd app && { [[ -d node_modules ]] || npm install --no-audit --no-fund; } && npm run build); }

cmd=${1:-all}
[[ $# -gt 0 ]] && shift
case "$cmd" in
  build)
    engine
    "$BIN" build --data data "$@"
    ;;
  serve)
    engine
    exec "$BIN" serve --data data --port "$PORT" --app app/dist "$@"
    ;;
  app)
    app
    ;;
  phone)
    # Geolocation and the service worker need HTTPS; Tailscale provides it.
    # Ports 443 and 8443 are often taken by other tools, so use 10000.
    tailscale serve --bg --https=10000 "http://127.0.0.1:$PORT"
    host=$(tailscale status --json | python3 -c "import json,sys; print(json.load(sys.stdin)['Self']['DNSName'].rstrip('.'))")
    echo "Open on your phone (Tailscale on):  https://$host:10000"
    ;;
  all)
    [[ -s data/raw/gtfs/gtfs.zip && -s data/raw/osm/switzerland-latest.osm.pbf ]] || scripts/fetch-data.sh
    engine
    "$BIN" build --data data
    [[ -f app/dist/index.html ]] || app
    exec "$BIN" serve --data data --port "$PORT" --app app/dist "$@"
    ;;
  *)
    sed -n '2,12p' "$0"
    exit 1
    ;;
esac
