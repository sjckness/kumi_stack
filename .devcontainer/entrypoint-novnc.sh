#!/usr/bin/env bash
# entrypoint-novnc.sh
# Starts a virtual display (Xvfb), a VNC server (x11vnc), and the noVNC web
# proxy (websockify), then hands control to the original container command.
set -e

DISPLAY_NUM=1
VNC_PORT=5900
NOVNC_PORT=6080
NOVNC_WEB=/usr/share/novnc/

# ---------- Xvfb -----------------------------------------------------------
echo "[novnc] Starting Xvfb on :${DISPLAY_NUM} ..."
Xvfb ":${DISPLAY_NUM}" -screen 0 1920x1080x24 +extension GLX +render -noreset &

export DISPLAY=":${DISPLAY_NUM}"

# Wait until the X server is accepting connections (up to 20 s).
for i in $(seq 1 40); do
    xdpyinfo -display ":${DISPLAY_NUM}" >/dev/null 2>&1 && break
    [ "$i" -eq 40 ] && { echo "[novnc] ERROR: Xvfb did not start within 20 s." >&2; exit 1; }
    sleep 0.5
done
echo "[novnc] Xvfb ready."

# ---------- x11vnc ---------------------------------------------------------
echo "[novnc] Starting x11vnc on 127.0.0.1:${VNC_PORT} ..."
x11vnc \
    -display ":${DISPLAY_NUM}" \
    -nopw \
    -listen 127.0.0.1 \
    -port  "${VNC_PORT}" \
    -xkb \
    -forever \
    -shared \
    >/tmp/x11vnc.log 2>&1 &

# ---------- websockify / noVNC ---------------------------------------------
echo "[novnc] Starting websockify on 0.0.0.0:${NOVNC_PORT} ..."
websockify --web="${NOVNC_WEB}" "${NOVNC_PORT}" "127.0.0.1:${VNC_PORT}" &
WSPY_PID=$!

# Wait until websockify is accepting connections (up to 10 s).
for i in $(seq 1 20); do
    if kill -0 "${WSPY_PID}" 2>/dev/null \
       && bash -c "echo >/dev/tcp/127.0.0.1/${NOVNC_PORT}" 2>/dev/null; then
        break
    fi
    [ "$i" -eq 20 ] && { echo "[novnc] ERROR: websockify did not start within 10 s." >&2; exit 1; }
    sleep 0.5
done

echo "[novnc] Ready — open http://localhost:${NOVNC_PORT}/vnc.html?autoconnect=true"

# ---------- hand off to original CMD ---------------------------------------
exec "$@"
