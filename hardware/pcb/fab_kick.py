"""JLCPCB assembly files for tx-kick: BOM and pick-and-place (CPL), in the
column layout of JLCPCB's samples (Sample-BOM_JLCSMT.xlsx, Sample-CPL_JLCSMT.xlsx).

Positions come from KiCad's own placement export, so they match the board.
Writes tx-kick/tx-kick_bom_jlc.{xlsx,csv} and tx-kick/tx-kick_cpl_jlc.{xlsx,csv},
and the Gerber and drill files, zipped for upload, in tx-kick/gerbers/.
"""
import csv, os, subprocess, tempfile
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(HERE, "tx-kick", "tx-kick.kicad_pcb")
OUT = os.path.join(HERE, "tx-kick")

# What JLCPCB is asked to fit, and the comment it matches parts by.
# Part numbers are left for JLCPCB's BOM matching or for you to fill in.
COMMENT = {   # short values, as in JLCPCB's sample; their matcher strips spaces
    "U1": "ATTINY85-20SU",
    "Q1": "AO3400A", "Q2": "AO3400A",
    "C3": "100nF", "C4": "10uF", "C5B": "22uF",
    "C5": "220uF",
    "RR": "10K", "RG": "47R", "RF": "47R", "RPD": "100K",
    "C1": "100nF C0G",
}
# Package names in the style of JLCPCB's library (the sample uses "R0603" and
# "CAP-SMD_L3.5-W2.8"). This column is only a label; placement uses the CPL.
JLC_FOOTPRINT = {
    "U1": "SOIC-8_L5.3-W5.3-P1.27", "Q1": "SOT-23-3", "Q2": "SOT-23-3",
    "C3": "C0402", "C4": "C0603", "C5B": "C0805", "C1": "C1206", "C5": "CAP-SMD_L3.5-W2.8",
    "RR": "R0402", "RG": "R0402", "RF": "R0402", "RPD": "R0402",
}
# Part numbers confirmed in JLCPCB's parts tool on 2026-10-02.
# C1 must be C0G/NP0: the matcher's first offer, C24497, is X7R and wrong.
LCSC = {
    "C1": "C2940749",       # C1206N104J101T, 100nF 100V NP0 +-5% 1206, Extended
    "C3": "C1525",          # 100nF 16V X7R 0402, Basic
    "C4": "C19702",         # 10uF 10V X5R 0603, Basic
    "C5B": "C45783",        # 22uF 25V X5R 0805, Basic
    "C5": "C2158369",       # Vishay T55B227M6R3C0035, 220uF 6.3V polymer, case B, Extended
    "Q1": "C20917", "Q2": "C20917",     # AO3400A SOT-23, Basic
    "RF": "C25118", "RG": "C25118",     # 47R 0402, Extended
    "RPD": "C25741",        # 100k 0402, Basic
    "RR": "C25744",         # 10k 0402, Basic
    "U1": "C31540447",      # ATTINY85-20SU SOIC-8 208mil, Extended
}
# Fitted by hand, so left out of both files:
#   BT1, BT2   battery pins           L1, L2   coil wire pads
#   C1T        tank trim capacitor, fitted only if tuning needs it
#   SW1        MK24-B-2 reed: out of stock at JLCPCB on 2026-10-02
#   J1.1-J1.4  programming pads (bare copper, not parts)
HAND_FIT = ["BT1", "BT2", "L1", "L2", "C1T", "SW1"]

# JLCPCB's part models do not always share KiCad's zero rotation. These
# offsets are added to KiCad's rotation in the CPL. Confirmed in JLCPCB's
# placement preview on 2026-10-02: SOT-23 parts showed turned 180 degrees, and
# the SOIC-8 turned 90 degrees so its pad rows sat over C3 and RR. KiCad draws
# SOIC-8 at zero with pin 1 top-left and pins down the sides; JLCPCB's model at
# zero has the pins along top and bottom with pin 1 bottom-left, so the
# correction is 270 (90 clockwise), which puts pin 1 back at top-left.
ROTATION_FIX = {"SOT-23": 180, "SOIC-8_5.23x5.23mm_P1.27mm": 270}

def kicad_positions():
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as t:
        path = t.name
    subprocess.run(["kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm",
                    "--side", "both", "-o", path, BOARD], check=True, capture_output=True)
    rows = list(csv.DictReader(open(path)))
    os.unlink(path)
    return {r["Ref"]: r for r in rows}

def write(name, header, rows):
    with open(os.path.join(OUT, name + ".csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Sheet1"
    ws.append(header)
    for r in rows: ws.append(r)
    wb.save(os.path.join(OUT, name + ".xlsx"))

def main():
    pos = kicad_positions()
    missing = [r for r in COMMENT if r not in pos]
    unplanned = [r for r in pos if r not in COMMENT and r not in HAND_FIT and not r.startswith("J1.")]
    assert not missing and not unplanned, (missing, unplanned)

    # BOM: one row per distinct comment and footprint
    groups = {}
    for ref, comment in COMMENT.items():
        groups.setdefault((comment, JLC_FOOTPRINT[ref], LCSC.get(ref, "")), []).append(ref)
    bom = [[c, ",".join(sorted(refs)), fp, pn] for (c, fp, pn), refs in sorted(groups.items(), key=lambda kv: sorted(kv[1])[0])]
    write("tx-kick_bom_jlc", ["Comment", "Designator", "Footprint", "JLCPCB Part #（optional）"], bom)

    # CPL: centre in mm with units, top/bottom as T/B, rotation 0-359
    cpl = []
    for ref in sorted(COMMENT):
        p = pos[ref]
        rot = (round(float(p["Rot"])) + ROTATION_FIX.get(p["Package"], 0)) % 360
        cpl.append([ref, f'{float(p["PosX"]):.4f}mm', f'{float(p["PosY"]):.4f}mm', "T" if p["Side"] == "top" else "B", rot])
    write("tx-kick_cpl_jlc", ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"], cpl)
    print(f"BOM: {len(bom)} lines, {sum(len(r[1].split(',')) for r in bom)} parts.  CPL: {len(cpl)} placements.  Hand-fit: {', '.join(HAND_FIT)}")

GERBER_LAYERS = ["F.Cu", "B.Cu", "F.Paste", "B.Paste", "F.SilkS", "B.SilkS", "F.Mask", "B.Mask", "Edge.Cuts"]

def gerbers():
    """Gerbers with Protel extensions and Excellon drill in mm, as JLCPCB asks."""
    import glob, shutil, zipfile
    gdir = os.path.join(OUT, "gerbers")
    shutil.rmtree(gdir, ignore_errors=True); os.makedirs(gdir)
    subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "--layers", ",".join(GERBER_LAYERS),
                    "--subtract-soldermask", "-o", gdir + "/", BOARD], check=True, capture_output=True)
    subprocess.run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm",
                    "--excellon-zeros-format", "decimal", "--drill-origin", "absolute", "-o", gdir + "/", BOARD],
                   check=True, capture_output=True)
    files = sorted(os.listdir(gdir))
    zpath = os.path.join(OUT, "tx-kick-gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(gdir, f), f)
    return gdir, files, zpath

if __name__ == "__main__":
    main()
    gdir, files, zpath = gerbers()
    print(f"Gerber and drill: {len(files)} files -> {os.path.relpath(zpath, HERE)}")
