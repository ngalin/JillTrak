"""Small two-layer grid router for tiny boards.

Rasterises every pad, finds each net's connections with A* over a 0.1 mm grid
on F.Cu and B.Cu (vias allowed at a cost), keeps DRC clearance to other nets'
copper and to the board edge, then straightens each path into as few segments
as stay clear. KiCad's own DRC is the final check; this only has to get close.
"""
import heapq, math
import numpy as np
from scipy.ndimage import distance_transform_edt
import pcbnew

G = 0.1                 # grid, mm
CLEAR = 0.15            # copper-to-copper clearance, mm
MARGIN = 0.1             # raster safety
EDGE = 0.3              # copper to board edge
VIA_D, VIA_DRILL = 0.6, 0.3
VIA_COST = 25.0

class Router:
    def __init__(self, board, radius, widths):
        self.b = board
        self.R = radius
        self.ext = radius + 0.3
        self.N = int(round(2 * self.ext / G)) + 1
        ax = -self.ext + np.arange(self.N) * G
        self.X, self.Y = np.meshgrid(ax, ax, indexing="xy")      # [row=y, col=x]
        self.rr = np.hypot(self.X, self.Y)
        self.widths = widths
        self.nets = [n for n in widths]
        self.copper = {n: [np.zeros((self.N, self.N), bool), np.zeros((self.N, self.N), bool)] for n in self.nets}
        self.padmask = {}       # (ref.pad) -> (mask, layers)
        self.anypad = np.zeros((self.N, self.N), bool)
        self.tracks, self.vias = [], []
        self._raster_pads()

    def ij(self, x, y):
        return int(round((y + self.ext) / G)), int(round((x + self.ext) / G))

    def xy(self, i, j):
        return -self.ext + j * G, -self.ext + i * G

    def _raster_pads(self):
        for fp in self.b.GetFootprints():
            for p in fp.Pads():
                net = p.GetNetname()
                cx, cy = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
                w, h = pcbnew.ToMM(p.GetSize().x), pcbnew.ToMM(p.GetSize().y)
                ang = math.radians(p.GetOrientation().AsDegrees())
                dx, dy = self.X - cx, self.Y - cy
                # pad frame (KiCad: y down, positive angle = counter-clockwise on screen)
                u = dx * math.cos(ang) - dy * math.sin(ang)
                v = dx * math.sin(ang) + dy * math.cos(ang)
                if p.GetShape() == pcbnew.PAD_SHAPE_CIRCLE:
                    m = np.hypot(dx, dy) <= w / 2
                else:
                    m = (np.abs(u) <= w / 2) & (np.abs(v) <= h / 2)
                layers = [L for L, cu in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)) if p.IsOnLayer(cu)]
                key = f"{fp.GetReference()}.{p.GetNumber()}"
                self.padmask[key] = (m, layers, net)
                self.anypad |= m
                if net in self.copper:
                    for L in layers:
                        self.copper[net][L] |= m
                else:   # unconnected pad: still an obstacle for everyone
                    self.copper.setdefault("_nc", [np.zeros_like(m), np.zeros_like(m)])
                    for L in layers:
                        self.copper["_nc"][L] |= m

    def _blocked(self, net):
        w = self.widths[net]
        out = []
        for L in (0, 1):
            other = np.zeros((self.N, self.N), bool)
            for n, cu in self.copper.items():
                if n != net:
                    other |= cu[L]
            d = distance_transform_edt(~other) * G
            out.append((d < CLEAR + w / 2 + MARGIN) | (self.rr > self.R - EDGE - w / 2))
        # via sites: clear on both layers for the via ring, not inside any pad, inside the edge
        vb = []
        for L in (0, 1):
            other = np.zeros((self.N, self.N), bool)
            for n, cu in self.copper.items():
                if n != net:
                    other |= cu[L]
            vb.append(distance_transform_edt(~other) * G < CLEAR + VIA_D / 2 + MARGIN)
        padd = distance_transform_edt(~self.anypad) * G < VIA_D / 2 + 0.05
        via_ok = ~(vb[0] | vb[1] | padd | (self.rr > self.R - EDGE - VIA_D / 2))
        return out, via_ok

    def _astar(self, net, sources, targets, blocked, via_ok):
        N = self.N
        tgt = targets
        ti, tj = np.nonzero(tgt[0] | tgt[1])
        tmin_i, tmax_i, tmin_j, tmax_j = ti.min(), ti.max(), tj.min(), tj.max()
        def h(i, j):
            di = 0 if tmin_i <= i <= tmax_i else min(abs(i - tmin_i), abs(i - tmax_i))
            dj = 0 if tmin_j <= j <= tmax_j else min(abs(j - tmin_j), abs(j - tmax_j))
            return math.hypot(di, dj)
        g = {}
        came = {}
        pq = []
        for L in (0, 1):
            si, sj = np.nonzero(sources[L])
            for i, j in zip(si, sj):
                s = (L, int(i), int(j)); g[s] = 0.0; came[s] = None
                heapq.heappush(pq, (h(i, j), 0.0, s))
        steps = [(-1, 0, 1), (1, 0, 1), (0, -1, 1), (0, 1, 1), (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)]
        while pq:
            f, gc, s = heapq.heappop(pq)
            if gc > g.get(s, 1e18): continue
            L, i, j = s
            if tgt[L][i, j]:
                path = []
                while s is not None:
                    path.append(s); s = came[s]
                return path[::-1]
            for di, dj, c in steps:
                ni, nj = i + di, j + dj
                if not (0 <= ni < N and 0 <= nj < N): continue
                if blocked[L][ni, nj] and not tgt[L][ni, nj] and not sources[L][ni, nj]: continue
                ns = (L, ni, nj); ng = gc + c
                if ng < g.get(ns, 1e18):
                    g[ns] = ng; came[ns] = s; heapq.heappush(pq, (ng + h(ni, nj), ng, ns))
            if via_ok[i, j]:
                ns = (1 - L, i, j); ng = gc + VIA_COST
                if not blocked[1 - L][i, j] and ng < g.get(ns, 1e18):
                    g[ns] = ng; came[ns] = s; heapq.heappush(pq, (ng + h(i, j), ng, ns))
        return None

    def _seg_clear(self, L, a, b, blocked, allow):
        (i1, j1), (i2, j2) = a, b
        n = int(max(abs(i2 - i1), abs(j2 - j1)) * 2) + 1
        for k in range(n + 1):
            t = k / n
            i = int(round(i1 + (i2 - i1) * t)); j = int(round(j1 + (j2 - j1) * t))
            if blocked[L][i, j] and not allow[L][i, j]:
                return False
        return True

    def _simplify(self, path, blocked, allow):
        """Split into same-layer runs and string-pull each run."""
        runs, cur = [], [path[0]]
        for s in path[1:]:
            if s[0] == cur[-1][0]:
                cur.append(s)
            else:
                runs.append(cur); cur = [s]
        runs.append(cur)
        out = []
        for run in runs:
            L = run[0][0]
            pts = [(s[1], s[2]) for s in run]
            keep = [pts[0]]; k = 0
            while k < len(pts) - 1:
                far = k + 1
                for m in range(len(pts) - 1, k, -1):
                    if self._seg_clear(L, pts[k], pts[m], blocked, allow):
                        far = m; break
                keep.append(pts[far]); k = far
            out.append((L, keep))
        return out

    def _paint_mask(self, mask, p1, p2, w):
        (x1, y1), (x2, y2) = p1, p2
        dx, dy = x2 - x1, y2 - y1
        l2 = dx * dx + dy * dy
        if l2 == 0:
            d = np.hypot(self.X - x1, self.Y - y1)
        else:
            t = np.clip(((self.X - x1) * dx + (self.Y - y1) * dy) / l2, 0, 1)
            d = np.hypot(self.X - (x1 + t * dx), self.Y - (y1 + t * dy))
        mask |= d <= w / 2

    def _paint_segment(self, net, L, p1, p2, w):
        (x1, y1), (x2, y2) = p1, p2
        dx, dy = x2 - x1, y2 - y1
        l2 = dx * dx + dy * dy
        if l2 == 0:
            d = np.hypot(self.X - x1, self.Y - y1)
        else:
            t = np.clip(((self.X - x1) * dx + (self.Y - y1) * dy) / l2, 0, 1)
            d = np.hypot(self.X - (x1 + t * dx), self.Y - (y1 + t * dy))
        self.copper[net][L] |= d <= w / 2

    def route_net(self, net, pins):
        blocked, via_ok = self._blocked(net)
        w = self.widths[net]
        def pinmask(p):
            m, layers, _ = self.padmask[p]
            return [m if 0 in layers else np.zeros_like(m), m if 1 in layers else np.zeros_like(m)]
        tree = pinmask(pins[0])
        routed = [np.zeros((self.N, self.N), bool), np.zeros((self.N, self.N), bool)]
        todo = list(pins[1:])
        # route to the nearest remaining pin each time
        while todo:
            ti, tj = np.nonzero(tree[0] | tree[1])
            cy, cx = ti.mean(), tj.mean()
            def dist(p):
                m = self.padmask[p][0]; a, bb = np.nonzero(m); return math.hypot(a.mean() - cy, bb.mean() - cx)
            todo.sort(key=dist)
            p = todo.pop(0)
            tgt = pinmask(p)
            path = self._astar(net, tree, tgt, blocked, via_ok)
            if path is None:
                raise RuntimeError(f"cannot route {net} to {p}")
            allow = [tree[0] | tgt[0], tree[1] | tgt[1]]
            runs = self._simplify(path, blocked, allow)
            for k, (L, pts) in enumerate(runs):
                xy = [self.xy(i, j) for i, j in pts]
                if len(xy) >= 2:
                    self.tracks.append((net, "F" if L == 0 else "B", w, [(round(x, 2), round(y, 2)) for x, y in xy]))
                    for a, b2 in zip(xy, xy[1:]):
                        self._paint_segment(net, L, a, b2, w)
                        self._paint_mask(routed[L], a, b2, w)
                if k < len(runs) - 1:
                    vx, vy = xy[-1]
                    self.vias.append((net, round(vx, 2), round(vy, 2)))
                    disc = np.hypot(self.X - vx, self.Y - vy) <= VIA_D / 2
                    self.copper[net][0] |= disc; self.copper[net][1] |= disc
                    routed[0] |= disc; routed[1] |= disc
            # the new copper joins the tree
            tree = [tree[0] | routed[0] | tgt[0], tree[1] | routed[1] | tgt[1]]
            # restrict tree to this net's copper only (pads + tracks)
        return True
