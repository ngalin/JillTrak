"""Schematic of the tx-kick PCB as a one-page A4 PDF: tx-kick/tx-kick-schematic.pdf.

Drawn as SVG and printed to PDF with headless Chrome. The circuit is the one
in build_kick.py; verify_kick.py checks the board against the same nets.
"""
import os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tx-kick")

T = 'font-family="DejaVu Sans Mono, monospace" font-size="13" fill="#111"'
TS = 'font-family="DejaVu Sans Mono, monospace" font-size="11" fill="#555"'
TN = 'font-family="DejaVu Sans Mono, monospace" font-size="11" fill="#0b5" font-style="italic"'

def res_v(x, y1, y2, ref, val, side=1):
    """Vertical resistor between y1 and y2 at x."""
    m = (y1 + y2) / 2
    tx = x + 14 if side > 0 else x - 14
    anc = "start" if side > 0 else "end"
    return (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{m-22}"/><rect x="{x-8}" y="{m-22}" width="16" height="44" fill="#fff"/>'
            f'<line x1="{x}" y1="{m+22}" x2="{x}" y2="{y2}"/>'
            f'<text x="{tx}" y="{m-3}" text-anchor="{anc}" {T} stroke="none">{ref}</text><text x="{tx}" y="{m+13}" text-anchor="{anc}" {TS} stroke="none">{val}</text>')

def res_h(x1, x2, y, ref, val):
    m = (x1 + x2) / 2
    return (f'<line x1="{x1}" y1="{y}" x2="{m-22}" y2="{y}"/><rect x="{m-22}" y="{y-8}" width="44" height="16" fill="#fff"/>'
            f'<line x1="{m+22}" y1="{y}" x2="{x2}" y2="{y}"/>'
            f'<text x="{m}" y="{y-14}" text-anchor="middle" {T} stroke="none">{ref}</text><text x="{m}" y="{y+26}" text-anchor="middle" {TS} stroke="none">{val}</text>')

def cap_v(x, y1, y2, ref, val, polar=False, side=1):
    m = (y1 + y2) / 2
    tx = x + 20 if side > 0 else x - 20
    anc = "start" if side > 0 else "end"
    bottom = (f'<path d="M{x-16},{m+10} Q{x},{m+2} {x+16},{m+10}"/>' if polar
              else f'<line x1="{x-16}" y1="{m+6}" x2="{x+16}" y2="{m+6}"/>')
    plus = f'<text x="{x+20}" y="{m-8}" {T} stroke="none">+</text>' if polar else ""
    return (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{m-6}"/><line x1="{x-16}" y1="{m-6}" x2="{x+16}" y2="{m-6}"/>{bottom}'
            f'<line x1="{x}" y1="{m+(8 if polar else 6)}" x2="{x}" y2="{y2}"/>{plus}'
            f'<text x="{tx}" y="{m-2}" text-anchor="{anc}" {T} stroke="none">{ref}</text><text x="{tx}" y="{m+14}" text-anchor="{anc}" {TS} stroke="none">{val}</text>')

def nmos(cx, cy, gate_left=True):
    """N-channel MOSFET, drain up at (cx+10, cy-40), source down at (cx+10, cy+40),
    gate lead ending at (cx-30, cy) (or mirrored when gate_left is False)."""
    s = 1 if gate_left else -1
    g = cx - 30 * s
    return (f'<line x1="{g}" y1="{cy}" x2="{cx-12*s}" y2="{cy}"/>'
            f'<line x1="{cx-12*s}" y1="{cy-16}" x2="{cx-12*s}" y2="{cy+16}" stroke-width="2.2"/>'
            f'<line x1="{cx-5*s}" y1="{cy-22}" x2="{cx-5*s}" y2="{cy-8}" stroke-width="2.6"/>'
            f'<line x1="{cx-5*s}" y1="{cy-6}" x2="{cx-5*s}" y2="{cy+6}" stroke-width="2.6"/>'
            f'<line x1="{cx-5*s}" y1="{cy+8}" x2="{cx-5*s}" y2="{cy+22}" stroke-width="2.6"/>'
            f'<line x1="{cx-5*s}" y1="{cy-15}" x2="{cx+10*s}" y2="{cy-15}"/><line x1="{cx+10*s}" y1="{cy-15}" x2="{cx+10*s}" y2="{cy-40}"/>'
            f'<line x1="{cx-5*s}" y1="{cy+15}" x2="{cx+10*s}" y2="{cy+15}"/><line x1="{cx+10*s}" y1="{cy+15}" x2="{cx+10*s}" y2="{cy+40}"/>'
            f'<line x1="{cx-5*s}" y1="{cy}" x2="{cx+10*s}" y2="{cy}"/><line x1="{cx+10*s}" y1="{cy}" x2="{cx+10*s}" y2="{cy+15}"/>'
            f'<polygon points="{cx-4*s},{cy} {cx+4*s},{cy-4} {cx+4*s},{cy+4}" fill="#111"/>')

def pad(x, y, label, anchor="start", dx=10):
    return (f'<circle cx="{x}" cy="{y}" r="5" fill="#fff"/>'
            f'<text x="{x+dx if anchor=="start" else x-dx}" y="{y+4}" text-anchor="{anchor}" {TS} stroke="none">{label}</text>')

def dot(x, y): return f'<circle cx="{x}" cy="{y}" r="3.2" fill="#111"/>'

def svg():
    VCC, GND = 110, 560
    o = []
    o.append(f'<line x1="70" y1="{VCC}" x2="930" y2="{VCC}"/>')
    o.append(f'<line x1="70" y1="{GND}" x2="975" y2="{GND}"/>')
    o.append(f'<text x="70" y="{VCC-12}" {T} stroke="none" font-weight="bold">VCC</text>')
    o.append(f'<text x="70" y="{GND+22}" {T} stroke="none" font-weight="bold">GND</text>')
    # battery: + via the side pin BT1 to VCC; - via the centre pin BT2 to Q1's drain
    bx = 130
    o.append(f'<line x1="{bx}" y1="{VCC}" x2="{bx}" y2="230"/>{dot(bx, VCC)}')
    for w, y in ((36, 230), (20, 240), (36, 254), (20, 264)):
        o.append(f'<line x1="{bx-w/2}" y1="{y}" x2="{bx+w/2}" y2="{y}" stroke-width="{2.4 if w == 20 else 1.6}"/>')
    o.append(f'<line x1="{bx}" y1="264" x2="{bx}" y2="330"/>')
    o.append(f'<text x="{bx-24}" y="238" text-anchor="end" {T} stroke="none">BT</text>'
             f'<text x="{bx-24}" y="254" text-anchor="end" {TS} stroke="none">2 × SR44</text>'
             f'<text x="{bx-24}" y="268" text-anchor="end" {TS} stroke="none">3.1 V</text>')
    o.append(f'<text x="{bx-6}" y="226" text-anchor="end" {T} stroke="none">+</text>')
    o.append(f'<text x="{bx-8}" y="160" text-anchor="end" {TS} stroke="none">BT1</text><text x="{bx-8}" y="173" text-anchor="end" {TS} stroke="none">side pin</text>')
    o.append(f'<text x="{bx-8}" y="300" text-anchor="end" {TS} stroke="none">BT2</text><text x="{bx-8}" y="313" text-anchor="end" {TS} stroke="none">centre pin</text>')
    # Q1 in the ground return: drain up to the cells, source down to GND, gate to VCC
    o.append(nmos(bx + 10, 370, gate_left=False))
    o.append(f'<line x1="{bx}" y1="410" x2="{bx}" y2="{GND}"/>{dot(bx, GND)}')
    o.append(f'<line x1="{bx+40}" y1="370" x2="175" y2="370"/><line x1="175" y1="370" x2="175" y2="{VCC}"/>{dot(175, VCC)}')
    o.append(f'<text x="{bx-24}" y="366" text-anchor="end" {T} stroke="none">Q1</text><text x="{bx-24}" y="382" text-anchor="end" {TS} stroke="none">AO3400A</text>')
    o.append(f'<text x="{bx-24}" y="398" text-anchor="end" {TN} stroke="none">reverse</text><text x="{bx-24}" y="411" text-anchor="end" {TN} stroke="none">polarity</text>')
    # decoupling
    o.append(cap_v(215, VCC, GND, "C4", "10µ")); o.append(dot(215, VCC)); o.append(dot(215, GND))
    o.append(cap_v(270, VCC, GND, "C3", "100n")); o.append(dot(270, VCC)); o.append(dot(270, GND))
    # U1
    ux1, ux2, uy1, uy2 = 360, 500, 180, 460
    o.append(f'<rect x="{ux1}" y="{uy1}" width="{ux2-ux1}" height="{uy2-uy1}" rx="3" fill="#f4f4f2"/>')
    o.append(f'<text x="{(ux1+ux2)/2}" y="{uy1+24}" text-anchor="middle" {T} stroke="none" font-weight="bold">U1</text>')
    o.append(f'<text x="{(ux1+ux2)/2}" y="{uy1+42}" text-anchor="middle" {TS} stroke="none">ATtiny85-20SU</text>')
    o.append(f'<line x1="430" y1="{VCC}" x2="430" y2="{uy1}"/>{dot(430, VCC)}<text x="438" y="{uy1-6}" {TS} stroke="none">8 VCC</text>')
    o.append(f'<line x1="430" y1="{uy2}" x2="430" y2="{GND}"/>{dot(430, GND)}<text x="438" y="{uy2+16}" {TS} stroke="none">4 GND</text>')
    # RESET: RR pull-up to VCC, RST programming pad below
    o.append(f'<line x1="320" y1="250" x2="{ux1}" y2="250"/><text x="{ux1+6}" y="254" {TS} stroke="none">1 RESET</text>')
    o.append(res_v(320, VCC, 250, "RR", "10k", side=-1)); o.append(dot(320, VCC)); o.append(dot(320, 250))
    o.append(f'<line x1="320" y1="250" x2="320" y2="385"/>' + f'<circle cx="320" cy="390" r="5" fill="#fff"/>'
             f'<text x="320" y="410" text-anchor="middle" {TS} stroke="none">J1.1 RST</text>')
    # right-hand pins; programming pads at the end of short stubs, labels above the stubs
    padx = ux2 + 80
    for n, name, y, lab in ((2, "PB3", 240, "n/c"), (3, "PB4", 280, ""), (7, "PB2", 340, "J1.2 SCK"),
                            (6, "PB1", 380, "J1.3 MISO"), (5, "PB0", 420, "J1.4 MOSI")):
        o.append(f'<text x="{ux2-6}" y="{y+4}" text-anchor="end" {TS} stroke="none">{name} {n}</text>')
        if n == 2:
            o.append(f'<line x1="{ux2}" y1="{y}" x2="{ux2+24}" y2="{y}"/><text x="{ux2+30}" y="{y+4}" {TS} stroke="none">n/c</text>')
            continue
        if n in (6, 5, 7):
            o.append(f'<line x1="{ux2}" y1="{y}" x2="{padx-5}" y2="{y}"/><circle cx="{padx}" cy="{y}" r="5" fill="#fff"/>')
            o.append(f'<text x="{ux2+8}" y="{y-6}" {TS} stroke="none">{lab}</text>')
    o.append(f'<text x="{ux2+8}" y="{380+16}" {TN} stroke="none">scope trigger</text>')
    # PB2 continues past its pad to the reed
    o.append(f'<line x1="{padx+5}" y1="340" x2="640" y2="340"/><line x1="640" y1="340" x2="640" y2="470"/>')
    o.append(f'<rect x="626" y="470" width="28" height="44" rx="14" fill="#fff"/><line x1="640" y1="470" x2="640" y2="480"/>'
             f'<line x1="640" y1="481" x2="650" y2="500"/><line x1="640" y1="504" x2="640" y2="{GND}"/>{dot(640, GND)}')
    o.append(f'<text x="620" y="492" text-anchor="end" {T} stroke="none">SW1</text><text x="620" y="508" text-anchor="end" {TS} stroke="none">MK24-B-2 reed</text>')
    # PB4 -> RG -> gate node; RPD to GND; Q2 gate
    o.append(f'<line x1="{ux2}" y1="280" x2="600" y2="280"/>')
    o.append(res_h(600, 700, 280, "RG", "47R"))
    o.append(f'<line x1="700" y1="280" x2="730" y2="280"/><line x1="730" y1="280" x2="730" y2="400"/><line x1="730" y1="400" x2="760" y2="400"/>{dot(730, 400)}')
    o.append(res_v(730, 400, GND, "RPD", "100k", side=-1)); o.append(dot(730, GND))
    o.append(f'<text x="722" y="392" text-anchor="end" {TN} stroke="none">GATE</text>')
    o.append(nmos(790, 400, gate_left=True))
    o.append(f'<line x1="800" y1="440" x2="800" y2="{GND}"/>{dot(800, GND)}')
    o.append(f'<text x="814" y="418" {T} stroke="none">Q2</text><text x="814" y="434" {TS} stroke="none">AO3400A</text>')
    o.append(f'<text x="814" y="450" {TN} stroke="none">kick switch</text>')
    # tank between TANK_B (x=800) and TANK_A (x=930)
    xb, xa = 800, 930
    o.append(f'<line x1="{xb}" y1="360" x2="{xb}" y2="230"/>')
    o.append(res_v(xa, VCC, 230, "RF", "47R", side=-1)); o.append(dot(xa, VCC))
    o.append(f'<line x1="{xa}" y1="230" x2="{xa}" y2="420"/>')
    mid = (xb + xa) / 2
    o.append(f'<line x1="{xb}" y1="230" x2="{mid-40}" y2="230"/>')
    o.append(f'<path d="M{mid-40},230 a8,8 0 0 1 16,0 a8,8 0 0 1 16,0 a8,8 0 0 1 16,0 a8,8 0 0 1 16,0 a8,8 0 0 1 16,0"/>')
    o.append(f'<line x1="{mid+40}" y1="230" x2="{xa}" y2="230"/>{dot(xb, 230)}{dot(xa, 230)}')
    o.append(f'<text x="{mid}" y="212" text-anchor="middle" {T} stroke="none">L  coil</text>')
    o.append(f'<text x="{mid}" y="248" text-anchor="middle" {TS} stroke="none">pads L1 / L2</text>')
    for y, lab, dashed in ((290, "C1  100n C0G", False), (345, "C1T  trim, optional", True)):
        da = ' stroke-dasharray="4 3"' if dashed else ""
        o.append(f'<line x1="{xb}" y1="{y}" x2="{mid-6}" y2="{y}"{da}/><line x1="{mid-6}" y1="{y-12}" x2="{mid-6}" y2="{y+12}"/>'
                 f'<line x1="{mid+6}" y1="{y-12}" x2="{mid+6}" y2="{y+12}"/><line x1="{mid+6}" y1="{y}" x2="{xa}" y2="{y}"{da}/>'
                 f'{dot(xb, y)}{dot(xa, y)}<text x="{mid}" y="{y+28}" text-anchor="middle" {TS} stroke="none">{lab}</text>')
    o.append(f'<text x="{xb-6}" y="226" text-anchor="end" {TN} stroke="none">TANK_B</text>'
             f'<text x="{xa+8}" y="268" {TN} stroke="none">TANK_A</text>')
    # reservoir C5 and C5B from TANK_A to GND
    o.append(cap_v(xa, 420, GND, "C5", "220µ 6.3V", polar=True, side=-1)); o.append(dot(xa, GND)); o.append(dot(xa, 420))
    o.append(f'<line x1="{xa}" y1="420" x2="975" y2="420"/>')
    o.append(cap_v(975, 420, GND, "", "", side=1)); o.append(dot(975, GND))
    o.append(f'<text x="990" y="486" {T} stroke="none">C5B</text><text x="990" y="502" {TS} stroke="none">22µ</text>')
    return o

NOTES = [
    "Ferret collar transmitter: transistor (\"kick\") drive, board tx-kick v0.1, 20 mm round",
    "Copies the Deben collar's timing: 148.9 kHz carrier, 11.1 ms bursts about every 189 ms.",
    "A magnet on reed SW1 latches transmission on and off. Between packets the ATtiny85 sleeps (< 1 µA).",
    "Each carrier cycle PB4 switches Q2 on for ~25 % (1.7 µs); the coil and C1 ring for the rest.",
    "C5 + C5B pay for each burst; the cells recharge them through RF between bursts.",
    "Q1 stops reversed cells from powering the circuit. C1 must be C0G/NP0 for frequency stability.",
    "Firmware: attiny85_kick build. Programming: J1.1-J1.4 plus the two battery pins.",
]

def build():
    body = "\n".join(svg())
    notes = "".join(f'<text x="70" y="{620 + 18*i}" {TS if i else T} stroke="none"{" font-weight=\'bold\'" if i == 0 else ""}>{n}</text>'
                    for i, n in enumerate(NOTES))
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>tx-kick schematic</title>
<style>@page {{ size: A4 landscape; margin: 10mm; }} html,body {{ margin:0; background:#fff; }}
svg {{ width: 277mm; height: 186mm; display:block; }}</style></head><body>
<svg viewBox="0 0 1040 760" xmlns="http://www.w3.org/2000/svg">
<rect x="20" y="20" width="1000" height="720" fill="none" stroke="#999" stroke-width="1"/>
<g stroke="#111" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round">
{body}
</g>
<line x1="20" y1="592" x2="1020" y2="592" stroke="#999"/>
{notes}
<text x="1005" y="730" text-anchor="end" {TS} stroke="none">ferrets project · hardware/schematic_kick.py · 2026-10-02</text>
</svg></body></html>"""
    html = os.path.join(OUT, "_schematic.html")
    open(html, "w").write(page)
    pdf = os.path.join(OUT, "tx-kick-schematic.pdf")
    subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", f"file://{html}"], check=True, capture_output=True, timeout=60)
    os.unlink(html)
    print("wrote", pdf, os.path.getsize(pdf), "bytes")

if __name__ == "__main__":
    build()
