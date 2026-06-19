#!/bin/bash
# chekreg — setup script
# Installs Python dependencies

set -e

echo ""
echo "  chekreg — Digital Footprint Mapper"
echo "  ──────────────────────────────────"
echo ""

# ── check Python ──────────────────────────────────────────────────────────────
if ! command -v python3 &> /dev/null; then
    echo "  ✗  Python 3 not found."
    echo "     Install it from https://www.python.org/downloads/ (3.8+ required)"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  ✓  Python $PYTHON_VERSION found"

# ── install dependencies ──────────────────────────────────────────────────────
echo ""
echo "  Installing dependencies…"
pip3 install --upgrade --quiet tldextract colorama flask duckduckgo-search requests
echo "  ✓  Dependencies installed"

# ── done ──────────────────────────────────────────────────────────────────────
echo ""
echo "  Setup complete. Run one of the following commands:"
echo ""
echo "    python3 chekreg.py         # Launch interactive selector"
echo "    python3 chekreg.py --web   # Launch Web Interface directly"
echo "    python3 chekreg.py --cli   # Launch Terminal Interface directly"
echo ""
