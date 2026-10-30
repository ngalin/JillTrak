"""Run KiCad's DRC on a board and render both copper sides to PNG."""
import os, re, subprocess, sys
import os
os.environ.setdefault('KICAD7_FOOTPRINT_DIR', '/usr/share/kicad/footprints')
import pcbnew
path = sys.argv[1]
out = os.path.splitext(path)[0]
b = pcbnew.LoadBoard(path)
rep = out + "-drc.rpt"
pcbnew.WriteDRCReport(b, rep, pcbnew.EDA_UNITS_MILLIMETRES, True)
txt = open(rep).read()
viol = re.findall(r"^\[(\w+)\]: (.*)$", txt, re.M)
unconn = re.search(r"\*\* Found (\d+) unconnected pads", txt)
nviol = re.search(r"\*\* Found (\d+) DRC violations", txt)
print(f"DRC violations: {nviol.group(1) if nviol else '?'}   unconnected: {unconn.group(1) if unconn else '?'}")
from collections import Counter
for k, v in Counter(k for k, _ in viol).most_common(): print(f"   {v:3} {k}")
for k, d in viol[:12]: print("     ", k, d[:110])
import tempfile
for side, layers in (("top", "F.Cu,F.SilkS,F.Fab,Edge.Cuts"), ("bottom", "B.Cu,B.SilkS,Edge.Cuts")):
    svg = f"{out}-{side}.svg"
    cmd = ["kicad-cli", "pcb", "export", "svg", "--layers", layers, "--page-size-mode", "2", "--exclude-drawing-sheet", "-o", svg, path]
    if side == "bottom": cmd.insert(4, "--mirror")
    subprocess.run(cmd, check=True, capture_output=True)
    png = f"{out}-{side}.png"
    # Chrome only loads the drawing from a page in the same folder
    page = os.path.join(os.path.dirname(os.path.abspath(svg)), f"_render-{side}.html")
    with open(page, "w") as h:
        h.write(f'<html><body style="margin:0;background:#fff"><img src="{os.path.basename(svg)}" style="width:900px;height:900px;object-fit:contain"></body></html>')
    subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars", "--window-size=900,900",
                    f"--screenshot={os.path.abspath(png)}", f"file://{page}"], capture_output=True, timeout=60)
    os.unlink(page)
    assert os.path.getsize(png) > 20000, f"{png} looks blank"
print("renders written")
