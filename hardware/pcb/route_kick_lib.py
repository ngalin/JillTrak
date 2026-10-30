"""Routing of the tx-kick board as a function, for route_kick.py and optimise_kick.py."""
import build_kick as bk
from router import Router

WIDTHS = {"TANK_A": 0.5, "TANK_B": 0.5, "GND": 0.4, "VCC": 0.35, "BATNEG": 0.4,
          "PB4": 0.2, "GATE": 0.25, "RESET": 0.2, "PB2": 0.2, "PB0": 0.2, "PB1": 0.2}
ORDER = ["TANK_A", "TANK_B", "BATNEG", "GND", "VCC", "GATE", "PB4", "RESET", "PB2", "PB1", "PB0"]

def route(order=ORDER, log=print):
    """Place from bk.PARTS and route every net. Returns (tracks, vias, failed)."""
    b, nets = bk.make_board()
    bk.place(b, nets)
    r = Router(b, bk.R_BOARD, WIDTHS)
    failed = []
    for net in order:
        keys = [f"{p}.1" if p.startswith("J1.") else p for p in bk.NETS[net]]   # ISP pads: footprint J1.n, pad 1
        try:
            r.route_net(net, keys); log(f"{net:7} ok")
        except RuntimeError as e:
            log(f"{net:7} FAIL {e}"); failed.append(net)
    return r.tracks, r.vias, failed
