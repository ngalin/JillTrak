#!/bin/sh
# Route, build and check the transistor-drive board.
# First time:  python3 -m venv --system-site-packages .venv && .venv/bin/pip install numpy scipy matplotlib openpyxl
cd "$(dirname "$0")"
PY=.venv/bin/python
$PY route_kick.py "$@" && $PY build_kick.py && $PY verify_kick.py && $PY check_board.py tx-kick/tx-kick.kicad_pcb && $PY fab_kick.py
