#!/bin/bash
# launch.sh — Launch PVT Calculator on local network.
#
# Usage:  ./launch.sh
# Then open  http://<mac-ip>:8501  on any device on the same WiFi.

# ── Find local IP ────────────────────────────────────────────────────────────
IP=$(ipconfig getifaddr en0 2>/dev/null \
  || ipconfig getifaddr en1 2>/dev/null \
  || ipconfig getifaddr en2 2>/dev/null \
  || echo "unknown")

echo ""
echo "========================================"
echo "  PVT Calculator starting..."
echo ""
if [ "$IP" = "unknown" ]; then
    echo "  Could not detect local IP."
    echo "  Try: System Settings → WiFi → Details"
else
    echo "  Open on your phone:"
    echo "  http://$IP:8501"
fi
echo "========================================"
echo ""

# ── Move to the script's own directory ───────────────────────────────────────
cd "$(dirname "$0")"

# ── Activate virtualenv if present ───────────────────────────────────────────
if [ -f .venv/bin/activate ]; then
    # shellcheck source=/dev/null
    source .venv/bin/activate
elif [ -f venv/bin/activate ]; then
    # shellcheck source=/dev/null
    source venv/bin/activate
fi

# ── Launch Streamlit on all interfaces ───────────────────────────────────────
exec streamlit run app.py \
    --server.address 0.0.0.0 \
    --server.port 8501 \
    --server.headless true
