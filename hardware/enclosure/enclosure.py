"""JillTrak collar enclosure (design v11): two halves with strap ears, as on the Deben. Two SR936 side by side in
series (3.1 V, the Deben's own cells), v0.1 board, no springs.

v10 = v9 with the cells beside each other instead of stacked: v9 was 16.3 mm thick, v10 is
12.7 (v8 with one CR1632 was 12.3). Two 9.9 mm wells with a 0.8 mm web between them fill the
boss, so the boss grows from 21.6 to 22.2 mm across (0.8 mm wall at the ends of the wells),
the cap's thread with it, and the thread-seal O-ring (22 x 1) now sits right against it. The front half is v8's.
Printed rim down, the boss is near solid round two small wells, so it cannot tear off the
floor the way v8's thin thread ring did.

Electrical path (cell A at -CELL_SEP along BT1's direction, cell B at +CELL_SEP):
- B sits + DOWN, its can on BT1's pin, which comes up through the floor under B and is cut
  flush with the well floor.
- A sits - DOWN, its negative cap on the centre pin (BT2), which comes up through the floor
  under the web between the wells, is bent over once into a groove in the floor and ends
  under A's centre. Sleeve or tape it where it passes under A's can rim (A's can is +).
- The round disc in the cap touches A's can (+, up) and B's negative cap (-, up): the disc
  is the series link, so it works at whatever angle the cap stops. A 21 x 1 O-ring between
  the disc and the cap ceiling presses it down (no pad, no spring); glue disc and O-ring into
  the cap so they come away with it. The cells stand CELL_PROUD above the rim, so the disc
  always bears on them and never on the plastic.

Layout (front = outside, back = the ferret's neck)
- FRONT HALF (shell): unchanged from v8: board parts facing out, reed about 2.5 mm under the
  front face (engraved ring marks the magnet spot), coil around the board, two strap ears.
- INSERT: glued into the shell from the back, under the back half. Coil former with a lead
  hole at the flange end and a slit through the lip, the floor, the two cell wells, the pin groove, male thread, O-ring groove.
- BACK HALF (cap): matching ears and the strap channel across its back, sloping into the ear
  slots. Screws on about one turn; the thread is timed so the ears line up when it is home.
- STRAP: down through one ear pair, across the back, up through the other; it locks the
  halves shut. Take it out to change cells.

Units mm. z = 0 is the front face, z grows towards the neck. Body x/y are seen from the
front; the board's component side faces the front, so board coordinates are used as they
are. y is the long axis, along the strap.

    python enclosure.py            (needs CadQuery 2.x; see README.md)
writes stl/shell.stl, stl/insert.stl, stl/cap.stl next to this file, each turned the way it
prints and sitting on z = 0: shell front down, insert rim down, cap back down.
"""
import math, os
import cadquery as cq

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")

# --- FIT: clearances to tune after a test print ------------------------------------------
CLR_CELL = 0.2                       # radial, cell in its recess (v7 had 0.4: loose)
CLR_PCB = 0.3                        # radial, board edge in the coil former (v7 had 0.05: tight)
CLR_GLUE = 0.15                      # radial, insert flange in the shell's counterbore: a glue gap, not a press fit
THREAD_CLR = 0.3                     # normal to the thread flanks, and at crest and root (0.2 bound up in PLA,
                                     # stopping the cap 1 mm short; only the cap's groove uses it)
THREAD_PHASE = 0.0                   # degrees: if the ears stop short of lining up, add that angle

# --- cells: two SR936 (SR936SW, 9.5 x 3.6) side by side, in series ----------------------
CELL_D, CELL_H = 9.5, 3.6
R_REC = CELL_D / 2 + CLR_CELL
WEB = 0.8                            # wall between the two wells
CELL_SEP = R_REC + WEB / 2           # each well's centre from the middle, along BT1's direction
FLOOR_CHAMFER = 0.25                 # 45 degree fillet round each well floor; the cells' rounded edges clear it
PIN_GROOVE_W, PIN_GROOVE_D = 0.9, 0.75   # bent centre pin (0.64 square, plus tape) lies flush in the floor
PIN_NOTCH_W = 1.4                    # gap through the web over the centre pin, room to bend it over

# --- board (v0.1), board coordinates = body coordinates -----------------------------
PCB_D, PCB_T = 20.0, 1.6
SIDE_PIN = (6.2, 5.6)                # BT1, seen from the component side
COIL_HOLES = [(-5.85, 6.45), (-8.6, -0.6)]   # L1, L2
SW1 = (7.4, -0.2)                    # reed, 5.0 x 2.2 mm along y
SW1_BODY_H = 2.2
TH_JOINTS = [(0.0, 0.0), SIDE_PIN] + COIL_HOLES   # solder joints poking out of the pin side
POST_ANGLES = (0, 80, 200, 320)      # where nothing on the component side reaches the edge
WIRE_D = 0.8                         # BT1's pin or a 0.8 wire in its place, straight up

# --- stack, front to back ---------------------------------------------------------------
FRONT_T = 1.2
COMP_H = 2.5                         # reed is 2.2-2.3 tall: keep it off the front face
Z_PCB = FRONT_T + COMP_H             # component face
Z_BACK = Z_PCB + PCB_T               # pin face, against the insert floor
FLOOR_T = 1.2
Z_FLOOR = Z_BACK + FLOOR_T           # cell's negative face
CELL_PROUD = 0.3                     # cells stand this far above the rim: the disc bears on them, not the plastic
Z_CELL_TOP = Z_FLOOR + CELL_H
Z_RIM = Z_CELL_TOP - CELL_PROUD
DISC_T = 0.3                         # brass or copper contact disc
DORING_ID, DORING_CS = 21.0, 1.0     # O-ring pressing the disc's rim onto the cells; held in the cap bore by its
                                     # own radial squeeze (23 OD in a 22.7 bore)
DORING_SQUEEZE = 0.25                # 1.0 squeezed to 0.75: takes up about +-0.25 of cell and print tolerance
Z_CEIL = Z_CELL_TOP + DISC_T + DORING_CS * (1 - DORING_SQUEEZE)
CAP_T = 1.6
Z_TOP = Z_CEIL + CAP_T               # back face, against the neck
Z_PART = Z_FLOOR - 0.4               # parting plane between the halves
Z_FLANGE = Z_PART - 1.4              # insert flange underside (carries the O-ring groove)

# --- plan --------------------------------------------------------------------------------
R_BOSS_FRONT = 13.2                  # round front boss
EAR_Z0 = 1.5                         # ears start this far behind the front face
SLOT_L, SLOT_W, BAR_W = 13.0, 2.6, 2.5
SLOT_Y = R_BOSS_FRONT + 0.1 + SLOT_W / 2
LEN = 2 * (SLOT_Y + SLOT_W / 2 + BAR_W)
R_BODY = 13.4                        # round body in plan
EAR_W = 17.4                         # ear tab width: slot plus a 2.2 mm bar each side
EAR_R = 4.5                          # ear tip corner radius
NECK_R = 4.0                         # inside curve where the ear tab meets the round body
EAR_TIP_Z = 3.8                      # front half's ears slope back from the boss to this at the tip (2.3 thick)
WID = 2 * R_BODY
CHANNEL_W, CHANNEL_D = 10.8, 0.8     # strap channel across the back: 0.8 leaves 0.8 over the cell pocket
CHANNEL_R = 2.0                      # the channel rolls over into each ear slot on a 2 mm radius: the strap
                                     # folds over a quarter round, not a corner (0.75 left over the O-ring pocket)
CHANNEL_D_EAR = CHANNEL_D + CHANNEL_R
CAP_EAR_TIP = 2.6                    # back half's ears slope down to this thickness at the tips
CAP_TAPER_Y0 = 12.6                  # the slope starts here, just outside the round body's thread
BACK_R = 3.0                         # roll on the back half's back edge: softer on the neck, lighter ears

# --- inside the shell ----------------------------------------------------------------------
R_BAY = 12.35                        # coil + parts bay: room for 19 turns of 0.31 wire in three layers (to r 12.2)
R_CBORE = 12.5                       # counterbore the insert flange is glued into; the flange does not sit on its
                                     # step: the skirt's end rests on the inside of the front instead
R_POST_IN = 9.3

# --- insert ----------------------------------------------------------------------------------
R_FLANGE = R_CBORE - CLR_GLUE
R_SKIRT_IN = PCB_D / 2 + CLR_PCB     # coil former, just outside the board edge
R_SKIRT = R_SKIRT_IN + 0.85          # 0.85 wall = two 0.4 nozzle lines
R_LIP = R_SKIRT + 0.7                 # holds two of the coil's three layers                        # lip at the front end of the former
Z_SKIRT0 = FRONT_T                   # skirt end rests on the inside of the front: locates the insert
R_BOSS = 11.1                        # 22.2 across: two 9.9 wells, 0.8 web, 0.8 wall at each end
THREAD_H = 0.6                       # ridge height above the boss
THREAD_W = 1.4                       # ridge width at the boss; 45 degree flanks, so 0.2 at the crest
THREAD_LEAD = 3.2                    # two starts, 1.6 apart: about one turn to close
THREAD_Z0, THREAD_Z1 = Z_PART + 0.4, Z_PART + 3.0   # male ridges on the insert boss
THREAD_GROOVE_Z1 = THREAD_Z1 + 1.1   # cap groove's top end: the ridge's top plus the 0.88 play, kept below the disc O-ring pocket
ORING_CS = 1.0
R_ORING_IN, R_ORING_OUT = R_BOSS, R_BOSS + 1.0   # 22 x 1, stretched 1 % onto the boss, sitting against it
ORING_DEPTH = ORING_CS - 0.25
RELIEF_D, RELIEF_H = 2.6, 0.5
CELL_ROT = 12.0                      # cells turned this far off the BT1 line, so L2's lead hole clears well A
LEAD_HOLE_D = 0.9                    # coil leads go on through L1/L2 and up through the floor to the rim,
LEAD_SINK_D, LEAD_SINK_H = 1.8, 0.4  # to be pulled taut from the cell side; trimmed and glued in this sink
COIL_HOLE_D = 0.8                    # coil-end holes for 0.31 wire, one at each end of the channel
Z_COIL_START = Z_FLANGE - COIL_HOLE_D / 2 - 0.05             # start hole: the channel's flange end
COIL_SLIT_W = 0.6                    # finish lead: slit through the lip, open at the front end
COIL_SLIT_Z1 = Z_SKIRT0 + 0.3 + (R_LIP - R_SKIRT) + 0.35   # slit reaches the first turn beside the lip
LEAD_GROOVE_W = 0.6                  # start lead's groove down the bore
LEAD_GROOVE = 0.3                    # groove depth in the bore: lead clears the board edge (0.3 gap, 0.35 wire)

# --- cap ----------------------------------------------------------------------------------------
R_CAP_BORE = R_BOSS + 0.25
R_LEAD_IN = R_CAP_BORE + 0.15       # small lead-in, so the face still presses most of the O-ring
R_DISC = 11.2                        # 22.4 across: covers both cells, and its rim reaches under the O-ring (r 10.5 to 11.5)

# --- marks --------------------------------------------------------------------------------------
MARK_D, MARK_W, MARK_DEPTH = 6.0, 0.6, 0.3
# GALT logo (a "G" over a bar) engraved in the front, reading upright with the strap horizontal:
# the logo's up is +x, towards the magnet ring. Two 0.16 layers deep, like the ring.
LOGO_H = 7.5                         # cap height of the G
LOGO_DEPTH = 0.32
LOGO_X = -2.0                        # centre of the G along x
LOGO_FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

def cyl(r, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).circle(r).extrude(z1 - z0)

def ring(r0, r1, z0, z1):
    return cyl(r1, z0, z1).cut(cyl(r0, z0, z1))

def radial_box(r0, r1, w, z0, z1, ang):
    return (cq.Workplane("XY").workplane(offset=z0).center((r0 + r1) / 2, 0)
            .rect(r1 - r0, w).extrude(z1 - z0).rotate((0, 0, 0), (0, 0, 1), ang))

def revolve(pts):
    return cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0))

def outline(z0, z1):
    """Plan: a round body with two narrower ear tabs, blended with inside curves."""
    tab = (cq.Workplane("XY").workplane(offset=z0).rect(EAR_W, LEN).extrude(z1 - z0)
           .edges("|Z").fillet(EAR_R))
    o = cyl(R_BODY, z0, z1).union(tab)
    yj = math.sqrt(R_BODY ** 2 - (EAR_W / 2) ** 2)          # where the tab sides meet the circle
    sel = None
    for sx in (1, -1):
        for sy in (1, -1):
            b = cq.selectors.BoxSelector((sx * EAR_W / 2 - 0.2, sy * yj - 0.2, z0 - 1),
                                         (sx * EAR_W / 2 + 0.2, sy * yj + 0.2, z1 + 1))
            sel = b if sel is None else sel + b
    return o.edges(sel).fillet(NECK_R)

def ear_taper():
    """Wedges that slope the front half's ears back from the boss to EAR_TIP_Z at the tips."""
    out = None
    for s in (1, -1):
        w = (cq.Workplane("YZ").polyline([(R_BOSS_FRONT - 0.6, EAR_Z0 - 0.01), (LEN / 2 + 1, EAR_TIP_Z),
                                          (LEN / 2 + 1, -2), (R_BOSS_FRONT - 0.6, -2)]).close()
             .extrude(WID, both=True))
        if s < 0:
            w = w.mirror("XZ")
        out = w if out is None else out.union(w)
    return out.cut(cyl(R_BOSS_FRONT, -3, Z_PART))

def slots(z0, z1):
    out = None
    for s in (1, -1):
        sl = cq.Workplane("XY").workplane(offset=z0).center(0, s * SLOT_Y).slot2D(SLOT_L, SLOT_W).extrude(z1 - z0)
        out = sl if out is None else out.union(sl)
    return out

def helix_ridge(r0, r1, w0, z0, z1, dz=0.0):
    """Two-start right-hand thread ridge: (r0, width w0) to the crest r1, 45 degree flanks, clipped to z0..z1."""
    w1 = w0 - 2 * (r1 - r0)
    pts = [(r0, dz - w0 / 2), (r1, dz - w1 / 2), (r1, dz + w1 / 2), (r0, dz + w0 / 2)]
    # start a whole number of leads from Z_PART so both halves share one helix; keep the sweep short,
    # OCC booleans fail on long swept helices
    z_start = Z_PART + THREAD_LEAD * math.floor((z0 - 1.0 - Z_PART) / THREAD_LEAD)
    turns = (z1 + 1.0 - z_start) / THREAD_LEAD
    path = cq.Wire.makeHelix(THREAD_LEAD, THREAD_LEAD * turns, r0)
    one = (cq.Workplane("XZ").polyline(pts).close().sweep(cq.Workplane(obj=path), isFrenet=True)
           .translate((0, 0, z_start)).rotate((0, 0, 0), (0, 0, 1), THREAD_PHASE))
    both = one.union(one.rotate((0, 0, 0), (0, 0, 1), 180), tol=1e-3)
    return both.intersect(cyl(r1 + 1, z0, z1))

def coil_hole(ang, zc, groove=False):
    """Radial hole for a coil end. Teardrop, point towards the front: it prints rim down, point up.
    The start hole sits at the flange end, behind the board's component face, so a groove down the
    former's bore carries that lead past the board edge; the finish hole by the lip is already in
    front of the component face and its lead runs straight in."""
    r = COIL_HOLE_D / 2
    d = r / math.sqrt(2)
    prof = (cq.Workplane("YZ").workplane(offset=R_SKIRT_IN - 0.3).center(0, zc).circle(r).extrude(R_LIP - R_SKIRT_IN + 0.6)
            .union(cq.Workplane("YZ").workplane(offset=R_SKIRT_IN - 0.3)
                   .polyline([(-d, zc - d), (0, zc - r * math.sqrt(2)), (d, zc - d), (0, zc)]).close()
                   .extrude(R_LIP - R_SKIRT_IN + 0.6)))
    if groove:
        prof = prof.union(radial_box(R_SKIRT_IN - 0.3, R_SKIRT_IN + LEAD_GROOVE, LEAD_GROOVE_W, Z_SKIRT0 - 0.1, zc, 0))
    return prof.rotate((0, 0, 0), (0, 0, 1), ang)

def coil_slit(ang):
    """Finish lead: a narrow slit through the lip and former, open at the front end, down to
    the first turn, so the lead drops in from the end instead of being threaded."""
    return radial_box(R_SKIRT_IN - 0.3, R_LIP + 0.3, COIL_SLIT_W, Z_SKIRT0 - 0.1, COIL_SLIT_Z1, ang)

def cell_xy(k):
    """Centre of cell A (k = -1, minus down, on the bent centre pin) or B (k = +1, plus down, on BT1)."""
    a = math.radians(CELL_ANG)
    return k * CELL_SEP * math.cos(a), k * CELL_SEP * math.sin(a)

def ang_of(p):
    return math.degrees(math.atan2(p[1], p[0]))

CELL_ANG = ang_of(SIDE_PIN) + CELL_ROT   # the line through both cell centres

# ---------------------------------------------------------------------------------------------------
def logo():
    # plane facing out of the front (normal -z), so the G reads correctly from the front;
    # local x runs along +y and local y (the logo's up) along +x
    pl = cq.Plane(origin=(0, 0, LOGO_DEPTH), xDir=(0, 1, 0), normal=(0, 0, -1))
    g = cq.Workplane(pl).text("G", 1.0, 1.0, fontPath=LOGO_FONT, halign="center", valign="center")
    bb = g.val().BoundingBox()
    size = LOGO_H / bb.xlen                                 # the G's extent along global x = its height
    g = cq.Workplane(pl).text("G", size, LOGO_DEPTH + 0.1, fontPath=LOGO_FONT, halign="center", valign="center")
    bb = g.val().BoundingBox()
    g = g.translate((LOGO_X - (bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, 0))
    gap, bar_t, bar_w = 0.14 * LOGO_H, 0.12 * LOGO_H, 1.04 * LOGO_H   # proportions of the GALT mark
    xb = LOGO_X - LOGO_H / 2 - gap - bar_t / 2
    bar = cq.Workplane("XY").workplane(offset=-0.1).center(xb, 0).rect(bar_t, bar_w).extrude(LOGO_DEPTH + 0.1)
    return g.union(bar)

def shell():
    s = outline(EAR_Z0, Z_PART)
    s = s.cut(ear_taper())
    boss = revolve([(0, 0), (R_BOSS_FRONT - 1.0, 0), (R_BOSS_FRONT - 0.29, 0.29),
                    (R_BOSS_FRONT, 1.0), (R_BOSS_FRONT, EAR_Z0 + 0.5), (0, EAR_Z0 + 0.5)])
    s = s.union(boss)
    s = s.cut(slots(-1, Z_PART + 1))
    s = s.cut(cyl(R_BAY, FRONT_T, Z_FLANGE + 0.01))
    s = s.cut(cyl(R_CBORE, Z_FLANGE - 0.1, Z_PART + 1))   # step clear of the flange
    for a in POST_ANGLES:                                   # posts holding the board's edge
        s = s.union(radial_box(R_POST_IN, PCB_D / 2 + 0.05, 1.6, FRONT_T - 0.05, Z_PCB, a))   # stop short of the skirt
    s = s.cut(logo())
    rx, ry = SW1                                            # magnet spot over the reed
    s = s.cut(cq.Workplane("XY").workplane(offset=-0.1).center(rx, ry)
              .circle(MARK_D / 2).circle(MARK_D / 2 - MARK_W).extrude(MARK_DEPTH + 0.1))
    return s

def insert():
    # skirt (coil former) with a lip at its front end, floor + flange, boss. Prints rim down (the
    # front-down print needed support under the floor that broke the skirt getting it out): the lip's
    # back face is a 45 degree cone so it builds without support; only the flange's O-ring face and
    # the cell recess floor overhang, both reached from the bed
    prof = [(R_SKIRT_IN + 0.4, Z_SKIRT0), (R_LIP, Z_SKIRT0), (R_LIP, Z_SKIRT0 + 0.3),
            (R_SKIRT, Z_SKIRT0 + 0.3 + (R_LIP - R_SKIRT)), (R_SKIRT, Z_FLANGE), (R_FLANGE, Z_FLANGE), (R_FLANGE, Z_PART),
            (R_BOSS, Z_PART), (R_BOSS, Z_RIM - 0.3), (R_BOSS - 0.3, Z_RIM), (0, Z_RIM), (0, Z_BACK),
            (R_SKIRT_IN, Z_BACK), (R_SKIRT_IN, Z_SKIRT0 + 0.4)]
    i = revolve(prof)
    i = i.cut(coil_hole(ang_of(COIL_HOLES[1]), Z_COIL_START, groove=True))   # start lead, flange end, by L2
    i = i.cut(coil_slit(ang_of(COIL_HOLES[0])))                               # finish lead, slit in the lip, by L1
    i = i.union(helix_ridge(R_BOSS - 0.2, R_BOSS + THREAD_H, THREAD_W + 0.4, THREAD_Z0, THREAD_Z1), tol=1e-3)
    i = i.cut(ring(R_ORING_IN, R_FLANGE + 0.1, Z_PART - ORING_DEPTH, Z_PART + 0.1))   # open: the shell bore is its outer wall
    mouth = (cq.Workplane("XY").workplane(offset=Z_RIM - 0.3).circle(R_REC)        # chamfer: first-layer squish
             .workplane(offset=0.31).circle(R_REC + 0.31).loft())
    well = cyl(R_REC, Z_FLOOR + FLOOR_CHAMFER, Z_RIM + 1).union(
        cq.Workplane("XY").workplane(offset=Z_FLOOR).circle(R_REC - FLOOR_CHAMFER)
        .workplane(offset=FLOOR_CHAMFER + 0.01).circle(R_REC + 0.01).loft()).union(mouth)
    for k in (-1, 1):
        i = i.cut(well.translate((*cell_xy(k), 0)))
    u = CELL_ANG
    i = i.cut(cyl(0.55, Z_BACK - 0.1, Z_FLOOR + 0.1))         # centre pin, up under the web
    i = i.cut(radial_box(-PIN_NOTCH_W / 2, PIN_NOTCH_W / 2, PIN_NOTCH_W, Z_FLOOR - 0.1, Z_RIM + 1, u))   # notch in the web
    i = i.cut(radial_box(0.3, CELL_SEP + 0.6, PIN_GROOVE_W, Z_FLOOR - PIN_GROOVE_D, Z_FLOOR + 0.1, u + 180))  # groove to A
    for p in TH_JOINTS:                                     # reliefs over the pin-side joints
        i = i.cut(cq.Workplane("XY").workplane(offset=Z_BACK - 0.1).center(*p)
                  .circle(RELIEF_D / 2).extrude(RELIEF_H + 0.1))
    i = i.cut(cq.Workplane("XY").workplane(offset=Z_BACK - 0.1).center(*SIDE_PIN)   # + pin, up under cell B
              .circle((WIRE_D + 0.2) / 2).extrude(Z_FLOOR - Z_BACK + 0.2))
    for p in COIL_HOLES:                                    # coil leads: through the floor and boss to the rim
        i = i.cut(cq.Workplane("XY").workplane(offset=Z_BACK - 0.1).center(*p)
                  .circle(LEAD_HOLE_D / 2).extrude(Z_RIM - Z_BACK + 0.2))
        i = i.cut(cq.Workplane("XY").workplane(offset=Z_RIM - LEAD_SINK_H).center(*p)
                  .circle(LEAD_SINK_D / 2).extrude(LEAD_SINK_H + 0.1))
    w = math.radians(u - 90)                                # which way up, engraved on the rim beside each well,
                                                            # on the side away from the lead holes
    for k, t in ((-1, "+"), (1, "-")):
        x, y = cell_xy(k)
        i = i.cut(cq.Workplane("XY").workplane(offset=Z_RIM - 0.4)
                  .center(x + 7.2 * math.cos(w), y + 7.2 * math.sin(w)).text(t, 2.2, 0.5))
    return i

def cap_taper():
    """Wedges that slope the back half's ears down from the body to CAP_EAR_TIP at the tips."""
    out = None
    for sgn in (1, -1):
        w = (cq.Workplane("YZ").polyline([(CAP_TAPER_Y0, Z_TOP + 0.01), (LEN / 2 + 1, Z_PART + CAP_EAR_TIP),
                                          (LEN / 2 + 1, Z_TOP + 5), (CAP_TAPER_Y0, Z_TOP + 5)]).close()
             .extrude(WID, both=True))
        if sgn < 0:
            w = w.mirror("XZ")
        out = w if out is None else out.union(w)
    return out

def cap():
    c = outline(Z_PART, Z_TOP)
    c = c.edges(">Z").fillet(BACK_R)                         # generous roll round the whole back edge
    c = c.cut(cap_taper())                                  # ears slope down towards their tips
    c = c.cut(slots(Z_PART - 1, Z_TOP + 1))
    y_in, y_out = SLOT_Y - SLOT_W / 2, SLOT_Y + SLOT_W / 2  # strap channel: flat over the cell, sloping
    cy, cz = y_in - CHANNEL_R, Z_TOP - CHANNEL_D - CHANNEL_R  # quarter round from the flat into each slot
    arc = [(cy + CHANNEL_R * math.sin(math.pi / 2 * k / 16), cz + CHANNEL_R * math.cos(math.pi / 2 * k / 16)) for k in range(17)]
    half = arc + [(y_out - 0.3, cz), (y_out - 0.3, Z_TOP - 0.6), (LEN / 2 + 1, Z_TOP - 0.6), (LEN / 2 + 1, Z_TOP + 1)]   # inside the slot: no sliver on its outer wall
    pts = [(-y, z) for y, z in reversed(half)] + half + [(-(LEN / 2 + 1), Z_TOP + 1)]
    c = c.cut(cq.Workplane("YZ").polyline(pts[:-1]).close().extrude(CHANNEL_W / 2, both=True))
    c = c.cut(cyl(R_CAP_BORE, Z_PART - 0.1, Z_CEIL))
    # female thread: the male ridge grown by THREAD_CLR, and raised so that when the face meets
    # the front half the ridge already bears on the groove's lower flank, which holds the cap
    # down (snug = ears aligned)
    a = THREAD_CLR * math.sqrt(2)                           # axial clearance per flank at 45 degrees
    r_root = R_BOSS + THREAD_H + THREAD_CLR
    r0 = R_CAP_BORE - 0.15
    w0 = THREAD_W + 2 * a - 2 * (r0 - R_BOSS)
    c = c.cut(helix_ridge(r0, r_root, w0, Z_PART - 1.0, THREAD_GROOVE_Z1, dz=a))
    lead_in = (cq.Workplane("XZ").polyline([(0, Z_PART - 0.1), (R_LEAD_IN, Z_PART - 0.1),
                                            (R_CAP_BORE, Z_PART + R_LEAD_IN - R_CAP_BORE), (0, Z_PART + 1)])
               .close().revolve(360, (0, 0, 0), (0, 1, 0)))
    c = c.cut(lead_in)                                      # 45 degree chamfer at the mouth
    return c

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    parts = {"shell": shell(), "insert": insert(), "cap": cap()}
    flip = {"shell": False, "insert": True, "cap": True}    # print orientation: shell front down,
    for name, p in parts.items():                           # insert rim down, cap back down
        q = p.rotate((0, 0, 0), (1, 0, 0), 180) if flip[name] else p
        q = q.translate((0, 0, -q.val().BoundingBox().zmin))   # sitting on the bed at z = 0
        cq.exporters.export(q, os.path.join(OUT, f"{name}.stl"), tolerance=0.02, angularTolerance=0.1)
        vol = sum(s.Volume() for s in p.vals())
        print(f"{name:6s} {vol:7.0f} mm3 ({vol * 1.27e-3:.1f} g PETG)  valid={p.val().isValid()}")
    print(f"thickness {Z_TOP:.1f} mm, {WID:.1f} x {LEN:.1f} mm; reed axis {Z_PCB - SW1_BODY_H / 2:.1f} mm under the front")
