"""Independent check: read the saved board and confirm every part's pins sit on
the nets the transistor-drive circuit needs (the circuit the protoboard proved)."""
import pcbnew
b = pcbnew.LoadBoard("tx-kick/tx-kick.kicad_pcb")
pin = {}
for fp in b.GetFootprints():
    for p in fp.Pads():
        pin[f"{fp.GetReference()}.{p.GetNumber()}"] = p.GetNetname()
want = {
    # ATtiny85 SOIC-8: 1 RESET, 2 PB3 (unused, a net of its own), 3 PB4, 4 GND, 5 PB0, 6 PB1, 7 PB2, 8 VCC
    "U1.1": "RESET", "U1.2": "PB3", "U1.3": "PB4", "U1.4": "GND", "U1.5": "PB0", "U1.6": "PB1", "U1.7": "PB2", "U1.8": "VCC",
    # AO3400A SOT-23: 1 gate, 2 source, 3 drain
    "Q1.1": "VCC", "Q1.2": "GND", "Q1.3": "BATNEG",          # reverse protection in the ground return
    "Q2.1": "GATE", "Q2.2": "GND", "Q2.3": "TANK_B",         # kick switch pulls the tank's B end low
    "BT1.1": "VCC", "BT2.1": "BATNEG",                       # side + pin, centre - pin
    "RG.1": "PB4", "RG.2": "GATE", "RPD.1": "GATE", "RPD.2": "GND",
    "RF.1": "VCC", "RF.2": "TANK_A",                         # reservoir fed through RF
    "C5.1": "TANK_A", "C5.2": "GND",                         # tantalum: pad 1 is positive
    "C5B.1": "TANK_A", "C5B.2": "GND",
    "C1.1": "TANK_A", "C1.2": "TANK_B", "C1T.1": "TANK_A", "C1T.2": "TANK_B",
    "L1.1": "TANK_A", "L2.1": "TANK_B",                      # coil across the tank
    "C3.1": "VCC", "C3.2": "GND", "C4.1": "VCC", "C4.2": "GND",
    "RR.1": "VCC", "RR.2": "RESET", "SW1.1": "PB2", "SW1.2": "GND",
    "J1.1.1": "RESET", "J1.2.1": "PB2", "J1.3.1": "PB1", "J1.4.1": "PB0",   # RST, SCK, MISO, MOSI
}
bad = [(k, want[k], pin.get(k)) for k in want if pin.get(k) != want[k]]
extra = sorted(set(pin) - set(want))
print(f"{len(want)} pins checked, {len(bad)} wrong, {len(extra)} unexpected pads")
for k, w, g in bad: print(f"   {k}: want {w!r}, board has {g!r}")
for k in extra: print("   unexpected", k)
