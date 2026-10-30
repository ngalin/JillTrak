"""Generate the transistor-drive collar board (tx-kick) with the KiCad 7 API.

Single source for the layout: footprints, nets, placement and every track are
defined here. Run with:  python3 build_kick.py  [--plot]
Outputs hardware/tx-kick/tx-kick.kicad_pcb, a DRC report and preview images.
"""
import math, os, sys
import pcbnew
from fplib import mk24, batt_neg, batt_pos, coil_pad, isp_pad

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tx-kick")
LIB = "/usr/share/kicad/footprints/"
MM = pcbnew.FromMM
R_BOARD = 10.0           # 20 mm round

# ------------------------------------------------------------------ netlist --
NETS = {
    "VCC":    ["BT1.1", "Q1.1", "U1.8", "C3.1", "C4.1", "RF.1", "RR.1"],
    "BATNEG": ["BT2.1", "Q1.3"],
    "GND":    ["Q1.2", "U1.4", "C3.2", "C4.2", "SW1.2", "Q2.2", "RPD.2", "C5.2", "C5B.2"],
    "RESET":  ["U1.1", "RR.2", "J1.1"],
    "PB3":    ["U1.2"],
    "PB4":    ["U1.3", "RG.1"],
    "PB0":    ["U1.5", "J1.4"],
    "PB1":    ["U1.6", "J1.3"],
    "PB2":    ["U1.7", "SW1.1", "J1.2"],
    "GATE":   ["RG.2", "RPD.1", "Q2.1"],
    "TANK_A": ["RF.2", "C5.1", "C5B.1", "C1.1", "C1T.1", "L1.1"],
    "TANK_B": ["Q2.3", "C1.2", "C1T.2", "L2.1"],
}

# ---------------------------------------------------------------- parts -----
# ref: (footprint source, value, x, y, rotation degrees, layer)
STD = lambda lib, name: ("std", lib, name)
PARTS = {
    # chip in the upper half, centre pin below it
    "U1":  (STD("Package_SO", "SOIC-8_5.23x5.23mm_P1.27mm"), "ATtiny85-20SU", 0.0, -4.9, 0, "F"),
    "BT2": ("bneg", "-", 0.0, 0.0, 0, "F"),
    "RR":  (STD("Resistor_SMD", "R_0402_1005Metric"), "10k", 0.0, -8.45, 180, "F"),
    "C3":  (STD("Capacitor_SMD", "C_0402_1005Metric"), "100n", 3.4, -8.3, 180, "F"),   # right above U1 pin 8 (VCC)
    # power entry and reed on the right
    "SW1": ("mk24", "MK24-B-2", 7.4, -0.2, 270, "F"),
    "Q1":  (STD("Package_TO_SOT_SMD", "SOT-23"), "AO3400A", 3.4, 2.6, 180, "F"),
    "C4":  (STD("Capacitor_SMD", "C_0603_1608Metric"), "10u", 3.6, 5.2, 0, "F"),
    "BT1": ("bpos", "+", 6.2, 5.6, 0, "F"),
    # gate drive on the left, beside PB4
    "RG":  (STD("Resistor_SMD", "R_0402_1005Metric"), "47", -5.65, -4.4, 180, "F"),
    "RPD": (STD("Resistor_SMD", "R_0402_1005Metric"), "100k", -6.9, -5.45, 180, "F"),
    "Q2":  (STD("Package_TO_SOT_SMD", "SOT-23"), "AO3400A", -6.5, -1.9, 270, "F"),
    # tank on the left, reservoir along the bottom
    "C1":  (STD("Capacitor_SMD", "C_1206_3216Metric"), "100n C0G", -6.5, 2.4, 90, "F"),
    "C1T": (STD("Capacitor_SMD", "C_0603_1608Metric"), "C0G trim", -8.4, 2.4, 90, "F"),
    "L2":  ("coil", "coil B", -8.6, -0.6, 0, "F"),
    "L1":  ("coil", "coil A", -5.85, 6.45, 0, "F"),   # clear of C5's polarity mark
    "C5":  (STD("Capacitor_Tantalum_SMD", "CP_EIA-3528-21_Kemet-B"), "220u 6.3V", -2.4, 6.6, 0, "F"),
    "C5B": (STD("Capacitor_SMD", "C_0805_2012Metric"), "22u", -2.4, 3.9, 180, "F"),
    "RF":  (STD("Resistor_SMD", "R_0402_1005Metric"), "47", 0.5, 3.9, 180, "F"),
}
# ISP pads J1.1..4 = RST, SCK, MISO, MOSI beside their U1 pins. VCC and ground
# for programming come in through the battery pins.
ISP_ORDER = ["RST", "SCK", "MISO", "MOSI"]
ISP_XY = {1: (-5.75, -6.8), 2: (5.75, -5.53), 3: (5.75, -4.27), 4: (5.75, -3.0)}

def make_board():
    b = pcbnew.BOARD()
    ds = b.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.m_TrackMinWidth = MM(0.15)
    ds.m_ViasMinSize = MM(0.5)
    ds.m_MinThroughDrill = MM(0.3)
    ds.m_MinClearance = MM(0.15)
    ds.m_CopperEdgeClearance = MM(0.3)
    nc = ds.m_NetSettings.m_DefaultNetClass
    nc.SetClearance(MM(0.15)); nc.SetTrackWidth(MM(0.25)); nc.SetViaDiameter(MM(0.6)); nc.SetViaDrill(MM(0.3))
    # outline
    c = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_CIRCLE)
    c.SetLayer(pcbnew.Edge_Cuts); c.SetWidth(MM(0.1))
    c.SetCenter(pcbnew.VECTOR2I(0, 0)); c.SetEnd(pcbnew.VECTOR2I(MM(R_BOARD), 0))
    b.Add(c)
    nets = {}
    for name in NETS:
        ni = pcbnew.NETINFO_ITEM(b, name); b.Add(ni); nets[name] = ni
    return b, nets

def load_fp(b, src):
    if isinstance(src, tuple):
        fp = pcbnew.FootprintLoad(LIB + src[1] + ".pretty", src[2])
        fp.SetFPID(pcbnew.LIB_ID(src[1], src[2]))
        return fp
    return {"mk24": mk24, "bpos": batt_pos, "bneg": batt_neg, "coil": coil_pad}[src](b)

def shrink_fab_text(fp):
    """Small reference text on the assembly layer, so the drawing stays legible."""
    texts = [fp.Reference()] + [g for g in fp.GraphicalItems() if g.GetClass() == "FP_TEXT"]
    for t in texts:
        t.SetTextSize(pcbnew.VECTOR2I(MM(0.45), MM(0.45))); t.SetTextThickness(MM(0.07))

def place(b, nets):
    fps = {}
    for ref, spec in PARTS.items():
        src, val, x, y, rot, side = spec
        fp = load_fp(b, src)
        fp.SetReference(ref); fp.SetValue(val)
        fp.Reference().SetLayer(pcbnew.F_Fab); fp.Value().SetVisible(False)
        shrink_fab_text(fp)
        b.Add(fp)
        if side == "B":
            fp.Flip(fp.GetPosition(), False)
        fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        fp.SetOrientationDegrees(rot)
        fps[ref] = fp
    for i, name in enumerate(ISP_ORDER, 1):
        x, y = ISP_XY[i]
        fp = isp_pad(b); fp.SetReference(f"J1.{i}"); fp.SetValue(name)
        fp.Reference().SetLayer(pcbnew.F_Fab); fp.Value().SetVisible(False)
        shrink_fab_text(fp)
        b.Add(fp); fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        fps[f"J1.{i}"] = fp
    # nets onto pads
    for net, pins in NETS.items():
        for pin in pins:
            ref, num = pin.rsplit(".", 1)
            if ref == "J1":
                pads = list(fps[f"J1.{num}"].Pads())
            else:
                pads = [p for p in fps[ref].Pads() if p.GetNumber() == num]
            assert pads, f"no pad {pin}"
            for p in pads: p.SetNet(nets[net])
    for ref, fp in fps.items():
        for p in fp.Pads():
            if p.GetNetname() == "" and not (ref == "U1" and p.GetNumber() == "2"):
                raise SystemExit(f"unassigned pad {ref}.{p.GetNumber()}")
    return fps

SILK = [  # text, x, y, layer, size mm
    ("+", 6.2, 7.35, "F", 0.9),
    ("-", 1.55, 0.95, "F", 0.9),
    ("tx-kick v0.1", 0.0, 7.2, "B", 0.8),
]

def add_silk(b):
    for text, x, y, side, size in SILK:
        t = pcbnew.PCB_TEXT(b)
        t.SetText(text); t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        t.SetLayer(pcbnew.F_SilkS if side == "F" else pcbnew.B_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size))); t.SetTextThickness(MM(size * 0.15))
        if side == "B": t.SetMirrored(True)
        b.Add(t)

def pad_xy(fps, pin):
    ref, num = pin.rsplit(".", 1)
    fp = fps[f"J1.{num}"] if ref == "J1" else fps[ref]
    p = [p for p in fp.Pads() if ref == "J1" or p.GetNumber() == num][0]
    return pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)

def plot(b, fps, path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.add_patch(Circle((0, 0), R_BOARD, fill=False, lw=1.2))
    cols = {}
    palette = ["#d62728", "#2ca02c", "#1f77b4", "#ff7f0e", "#9467bd", "#8c564b", "#e377c2", "#17becf", "#bcbd22", "#7f7f7f", "#000000", "#aa3377"]
    for i, n in enumerate(NETS): cols[n] = palette[i % len(palette)]
    for ref, fp in fps.items():
        for p in fp.Pads():
            x, y = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
            bb = p.GetBoundingBox()
            w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
            onb = p.IsOnLayer(pcbnew.B_Cu) and not p.IsOnLayer(pcbnew.F_Cu)
            ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc=cols.get(p.GetNetname(), "#ccc"), alpha=0.25 if onb else 0.55, ec="k", lw=0.4))
        x, y = pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y)
        ax.text(x, y, ref if not ref.startswith("J1.") else fp.GetValue(), fontsize=7, ha="center", va="center")
    # airwires: chain each net in nearest-neighbour order
    for net, pins in NETS.items():
        pts = [pad_xy(fps, p) for p in pins]
        done = [pts[0]]; rest = pts[1:]
        while rest:
            best = min(((math.dist(a, r), a, r) for a in done for r in rest))
            _, a, r = best
            ax.plot([a[0], r[0]], [a[1], r[1]], color=cols[net], lw=0.8)
            done.append(r); rest.remove(r)
    for tr in b.GetTracks():
        if tr.GetClass() == "PCB_VIA":
            x, y = pcbnew.ToMM(tr.GetPosition().x), pcbnew.ToMM(tr.GetPosition().y)
            ax.add_patch(Circle((x, y), 0.3, fc="w", ec="k", lw=0.6))
        else:
            s, e = tr.GetStart(), tr.GetEnd()
            ax.plot([pcbnew.ToMM(s.x), pcbnew.ToMM(e.x)], [pcbnew.ToMM(s.y), pcbnew.ToMM(e.y)],
                    color=cols[tr.GetNetname()], lw=3 if tr.GetLayer() == pcbnew.F_Cu else 2, alpha=0.9 if tr.GetLayer() == pcbnew.F_Cu else 0.5,
                    ls="-" if tr.GetLayer() == pcbnew.F_Cu else "--")
    ax.set_xlim(-10.5, 10.5); ax.set_ylim(10.5, -10.5); ax.set_aspect("equal"); ax.grid(alpha=0.2)
    handles = [plt.Line2D([], [], color=c, lw=2, label=n) for n, c in cols.items()]
    ax.legend(handles=handles, fontsize=7, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.savefig(path, dpi=110, bbox_inches="tight")

# Specification for the BOM: value, description. Footprint comes from PARTS.
SPEC = {
    "U1": "ATtiny85-20SU, SOIC-8 0.208 in", "Q1": "AO3400A N-MOSFET, reverse-polarity", "Q2": "AO3400A N-MOSFET, kick switch",
    "C3": "100nF X7R 16V", "C4": "10uF X5R 6.3V", "RR": "10k 1%", "RG": "47R 1%", "RPD": "100k 1%", "RF": "47R 1%",
    "C5": "100-220uF 6.3V polymer tantalum, case B (e.g. KEMET T520B)", "C5B": "22uF X5R 6.3V",
    "C1": "Tank, 100nF C0G/NP0 50V", "C1T": "Tank trim, C0G/NP0, fit only if needed",
    "SW1": "Standex-Meder MK24-B-2 reed, lead design 2",
    "BT1": "Battery + side pin, 1.0mm, hand-fit", "BT2": "Battery - centre pin, 1.0mm, hand-fit",
    "L1": "Coil wire A, hand-solder", "L2": "Coil wire B, hand-solder",
}

def write_bom(fps):
    import csv
    rows = {}
    for ref, fp in fps.items():
        if ref.startswith("J1."): continue
        key = (SPEC[ref], str(fp.GetFPID().GetLibItemName()))
        rows.setdefault(key, []).append(ref)
    with open(os.path.join(OUT, "bom.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC"])
        for (comment, fpn), refs in sorted(rows.items(), key=lambda kv: kv[1][0]):
            w.writerow([comment, ",".join(sorted(refs)), fpn, ""])

def save_project(fps):
    """Project file, a project library holding the custom footprints, and the
    library table, so the board opens cleanly in KiCad."""
    libdir = os.path.join(HERE, "collar.pretty")
    os.makedirs(libdir, exist_ok=True)
    scratch = pcbnew.BOARD()
    for builder in (mk24, batt_neg, batt_pos, coil_pad, isp_pad):
        fp = builder(scratch)
        fp.SetReference("REF**"); fp.Reference().SetLayer(pcbnew.F_Fab)
        pcbnew.FootprintSave(libdir, fp)
    with open(os.path.join(OUT, "fp-lib-table"), "w") as f:
        std = sorted({src[1] for src, *_ in PARTS.values() if isinstance(src, tuple)})
        rows = ['  (lib (name "collar")(type "KiCad")(uri "${KIPRJMOD}/../collar.pretty")(options "")(descr "Ferret collar custom footprints"))']
        rows += [f'  (lib (name "{n}")(type "KiCad")(uri "${{KICAD7_FOOTPRINT_DIR}}/{n}.pretty")(options "")(descr "KiCad standard"))' for n in std]
        f.write("(fp_lib_table\n  (version 7)\n" + "\n".join(rows) + "\n)\n")
    pro = os.path.join(OUT, "tx-kick.kicad_pro")
    if not os.path.exists(pro):
        with open(pro, "w") as f:
            f.write('{\n  "meta": {"filename": "tx-kick.kicad_pro", "version": 1}\n}\n')

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    b, nets = make_board()
    fps = place(b, nets)
    try:
        from routes_kick import ROUTES, VIAS
    except ImportError:
        ROUTES, VIAS = [], []
    for net, layer, width, pts in ROUTES:
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1))); t.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
            t.SetWidth(MM(width)); t.SetLayer(pcbnew.F_Cu if layer == "F" else pcbnew.B_Cu)
            t.SetNet(nets[net]); b.Add(t)
    for net, x, y in VIAS:
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3))
        v.SetNet(nets[net]); b.Add(v)
    write_bom(fps)
    add_silk(b)
    path = os.path.join(OUT, "tx-kick.kicad_pcb")
    b.Save(path)
    save_project(fps)
    if "--plot" in sys.argv:
        plot(b, fps, os.path.join(OUT, "plan.png"))
    print("saved", path)
