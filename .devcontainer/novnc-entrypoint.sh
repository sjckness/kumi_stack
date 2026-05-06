#!/bin/bash
# Boots Xvfb → x11vnc → websockify and only prints "ready" once every
# component is actually accepting connections. Any process dying tears
# the container down so docker can restart it cleanly.
set -uo pipefail

XVFB_PID=""
X11VNC_PID=""
WEBSOCKIFY_PID=""

cleanup() {
  echo "[novnc] shutting down..."
  for pid in "$WEBSOCKIFY_PID" "$X11VNC_PID" "$XVFB_PID"; do
    [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Wait for $path to appear, but bail out fast if $pid dies first.
wait_for_path() {
  local path="$1" pid="$2" label="$3" timeout="${4:-30}"
  local elapsed=0
  while [ ! -e "$path" ]; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "[novnc] $label (pid $pid) exited before $path appeared" >&2
      exit 1
    fi
    if [ "$elapsed" -ge "$((timeout * 10))" ]; then
      echo "[novnc] timed out after ${timeout}s waiting for $label ($path)" >&2
      exit 1
    fi
    sleep 0.1
    elapsed=$((elapsed + 1))
  done
}

# Wait for $host:$port to accept TCP, but bail out fast if $pid dies first.
wait_for_port() {
  local host="$1" port="$2" pid="$3" label="$4" timeout="${5:-30}"
  local elapsed=0
  until (echo > "/dev/tcp/$host/$port") >/dev/null 2>&1; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "[novnc] $label (pid $pid) exited before $host:$port came up" >&2
      exit 1
    fi
    if [ "$elapsed" -ge "$((timeout * 10))" ]; then
      echo "[novnc] timed out after ${timeout}s waiting for $label ($host:$port)" >&2
      exit 1
    fi
    sleep 0.1
    elapsed=$((elapsed + 1))
  done
}

# ── 1. Xvfb ─────────────────────────────────────────────────────────────────
Xvfb :1 -screen 0 1920x1080x24 -ac &
XVFB_PID=$!
wait_for_path /tmp/.X11-unix/X1 "$XVFB_PID" "Xvfb"
export DISPLAY=:1
echo "[novnc] Xvfb ready on :1 (pid $XVFB_PID)"

# ── 2. x11vnc ───────────────────────────────────────────────────────────────
x11vnc -display :1 -nopw -forever -shared -noxdamage -rfbport 5900 \
       -localhost >/dev/null 2>&1 &
X11VNC_PID=$!
wait_for_port 127.0.0.1 5900 "$X11VNC_PID" "x11vnc"
echo "[novnc] x11vnc ready on 127.0.0.1:5900 (pid $X11VNC_PID)"

# ── 3. noVNC websocket proxy ────────────────────────────────────────────────
# --listen-host 0.0.0.0 forces an IPv4 wildcard bind. Browsers must connect
# via http://127.0.0.1:6080/... — using "localhost" can resolve to ::1 on
# some hosts and would fail the websocket handshake.
websockify --web /usr/share/novnc \
           --listen-host 0.0.0.0 \
           6080 127.0.0.1:5900 &
WEBSOCKIFY_PID=$!
wait_for_port 127.0.0.1 6080 "$WEBSOCKIFY_PID" "websockify"
echo "[novnc] websockify ready on 0.0.0.0:6080 (pid $WEBSOCKIFY_PID)"

echo ""
echo "================================================"
echo "  noVNC ready → http://127.0.0.1:6080/vnc.html"
echo "================================================"
echo ""

# Block until any of the three exits, then trap-cleanup tears down the rest.
wait -n "$XVFB_PID" "$X11VNC_PID" "$WEBSOCKIFY_PID"
exit $?
