#!/usr/bin/env bash
# Dev helper: (re)start the engine as a supervised user service, so it
# survives the shell that started it and comes back if it dies.
#   scripts/dev-serve.sh [target-dir] [port]
#   logs:  journalctl --user -u kante-engine -f      stop:  systemctl --user stop kante-engine
cd "$(dirname "$0")/.."
P=$(pwd -P); T=${1:-engine/target-server}; PORT=${2:-8080}
systemctl --user stop kante-engine 2>/dev/null
systemctl --user reset-failed kante-engine 2>/dev/null
systemd-run --user --quiet --unit=kante-engine --description="Kante engine (prototype)" --working-directory="$P" \
  -p Restart=always -p RestartSec=2 "$P/$T/release/kante" serve --data data --port "$PORT" --app app/dist
for i in $(seq 1 80); do curl -s -m 1 -o /dev/null "localhost:$PORT/api/meta" && break; sleep 0.25; done
journalctl --user -u kante-engine -n 30 --no-pager -o cat | grep -E 'ready in|listening|rror' | tail -3
