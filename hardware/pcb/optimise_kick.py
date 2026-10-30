"""Try each two-terminal part both ways round, keep flips that shorten the
routing (ground counted double), and write the winning rotations back into
build_kick.py. Run after changing placement, then ./route_all.sh.
"""
import io, contextlib, math, re
import build_kick as bk
import route_kick_lib as rk

FLIPPABLE = ["C1", "C1T", "C3", "C4", "C5", "C5B", "RF", "RG", "RPD", "RR"]

def score(tracks, vias):
    total = 0.0
    for net, layer, w, pts in tracks:
        length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        total += length * (2.0 if net == "GND" else 1.0)
    return total + 1.5 * len(vias)

def attempt():
    with contextlib.redirect_stdout(io.StringIO()):
        res = rk.route()
    if res is None:
        return None
    tracks, vias, failed = res
    return None if failed else (score(tracks, vias), tracks, vias)

def main():
    base = attempt()
    assert base, "current placement does not route"
    best = base[0]
    print(f"start: score {best:.1f}")
    improved = True
    while improved:
        improved = False
        for ref in FLIPPABLE:
            spec = list(bk.PARTS[ref])
            old = spec[4]
            spec[4] = (old + 180) % 360
            bk.PARTS[ref] = tuple(spec)
            r = attempt()
            if r and r[0] < best - 0.05:
                print(f"  flip {ref:4} {old:>3} -> {spec[4]:>3}: score {best:.1f} -> {r[0]:.1f}")
                best = r[0]; improved = True
            else:
                spec[4] = old; bk.PARTS[ref] = tuple(spec)
    # write rotations back
    src = open(bk.__file__).read()
    for ref in FLIPPABLE:
        rot = bk.PARTS[ref][4]
        pat = re.compile(r'(    "' + re.escape(ref) + r'":\s*\(.*?,\s*-?[\d.]+,\s*-?[\d.]+,\s*)(-?\d+)(,\s*"[FB]"\),)')
        src, n = pat.subn(lambda m: m.group(1) + str(rot) + m.group(3), src)
        assert n == 1, ref
    open(bk.__file__, "w").write(src)
    print(f"final: score {best:.1f} (started {base[0]:.1f})")

if __name__ == "__main__":
    main()
