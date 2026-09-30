"""Einfacher 2-Lagen-Maze-Router (A*) fuer CO2-Ampel.kicad_pcb.
Ausfuehren mit KiCad-Python:  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" Platine\\scripts\\route_pcb.py

GND wird nicht geroutet, sondern ueber die Masseflaechen auf beiden Lagen verbunden.
Loescht vorhandene Leiterbahnen/Vias und routet alle anderen Netze neu."""
import heapq
import math
import os
import sys

import numpy as np
import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_pcb import OX, OY, W, H, R_CORNER, HOLES, SLOT_X, SLOT_Y0, SLOT_Y1, SLOT_W, ROOT, PROJECT  # noqa: E402

P = 0.254                  # Rastermass (mm)
CLEAR = 0.3                # Mindestabstand Kupfer-Kupfer
EDGE_CLEAR = 0.5           # Abstand zur Platinenkante
VIA_D, VIA_DRILL = 0.8, 0.4
VIA_COST = 12.0            # in Rasterschritten
TURN_COST = 1.5
WIDTH = {"+5V": 0.5, "+3V3": 0.5}
DEFAULT_W = 0.3
HOLE_KEEPOUT = 3.0         # Radius um Montageloecher (Schraubenkopf)
ANTENNA = (26.3, 16.0, 35.5, 44.0)   # keine Leiterbahnen unter der WLAN-Antenne
SKIP = {"GND"}

NX, NY = int(W / P) + 1, int(H / P) + 1
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def cell(x, y):
    return int(round(x / P)), int(round(y / P))


def disk(r_cells):
    k = int(math.ceil(r_cells))
    return [(di, dj) for di in range(-k, k + 1) for dj in range(-k, k + 1) if di * di + dj * dj <= r_cells * r_cells]


def dilate(mask, r_mm):
    out = mask.copy()
    for di, dj in disk(r_mm / P):
        src = mask[max(0, -di):NX - max(0, di), max(0, -dj):NY - max(0, dj)]
        out[max(0, di):NX - max(0, -di), max(0, dj):NY - max(0, -dj)] |= src
    return out


def board_mask():
    xs = np.arange(NX)[:, None] * P
    ys = np.arange(NY)[None, :] * P
    inside = (xs >= 0) & (xs <= W) & (ys >= 0) & (ys <= H)
    r = R_CORNER
    for cx, cy in [(r, r), (W - r, r), (r, H - r), (W - r, H - r)]:
        corner = ((xs < r) if cx < W / 2 else (xs > W - r)) & ((ys < r) if cy < H / 2 else (ys > H - r))
        inside &= ~(corner & ((xs - cx) ** 2 + (ys - cy) ** 2 > r * r))
    h = SLOT_W / 2
    slot = (np.abs(xs - SLOT_X) <= h) & (ys >= SLOT_Y0 - h) & (ys <= SLOT_Y1 + h)
    inside &= ~slot
    return inside


class Router:
    def __init__(self, board):
        self.board = board
        self.nets = {}          # Netzname -> Index
        self.owner = [np.full((NX, NY), -1, np.int16), np.full((NX, NY), -1, np.int16)]
        self.hard = ~board_mask()
        self.hard_edge = dilate(self.hard, EDGE_CLEAR)
        xs = np.arange(NX)[:, None] * P
        ys = np.arange(NY)[None, :] * P
        self.keep = np.zeros((NX, NY), bool)
        for hx, hy in HOLES:
            self.keep |= (xs - hx) ** 2 + (ys - hy) ** 2 <= HOLE_KEEPOUT ** 2
        ax0, ay0, ax1, ay1 = ANTENNA
        self.keep |= (xs >= ax0) & (xs <= ax1) & (ys >= ay0) & (ys <= ay1)
        self.pads = []          # (netidx, layers, maske)
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                self.add_pad(pad)

    def netidx(self, name):
        if name not in self.nets:
            self.nets[name] = len(self.nets)
        return self.nets[name]

    def add_pad(self, pad):
        name = pad.GetNetname()
        n = self.netidx(name) if name else -2
        bb = pad.GetBoundingBox()
        x0, y0 = pcbnew.ToMM(bb.GetLeft()) - OX, pcbnew.ToMM(bb.GetTop()) - OY
        x1, y1 = pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY
        xs = np.arange(NX)[:, None] * P
        ys = np.arange(NY)[None, :] * P
        shape = pad.GetShape(pcbnew.F_Cu)
        cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
        if shape == pcbnew.PAD_SHAPE_CIRCLE:
            m = (xs - cx) ** 2 + (ys - cy) ** 2 <= rx * rx
        elif shape == pcbnew.PAD_SHAPE_OVAL:
            r = min(rx, ry)
            dx = np.maximum(np.abs(xs - cx) - (rx - r), 0)
            dy = np.maximum(np.abs(ys - cy) - (ry - r), 0)
            m = dx * dx + dy * dy <= r * r
        else:
            m = (np.abs(xs - cx) <= rx) & (np.abs(ys - cy) <= ry)
        if not m.any():
            m[cell(cx, cy)] = True
        layers = [i for i, L in enumerate((pcbnew.F_Cu, pcbnew.B_Cu)) if pad.IsOnLayer(L)]
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            self.hard |= m
            return
        for L in layers:
            self.owner[L][m] = n
        self.pads.append((n, layers, m, (cx, cy), pad))

    def blocked(self, n, width):
        """Zellen, auf denen die Mittellinie einer Bahn des Netzes n nicht liegen darf."""
        res = []
        for L in (0, 1):
            other = (self.owner[L] != -1) & (self.owner[L] != n)
            b = dilate(other, width / 2 + CLEAR + P * 0.75)
            b |= dilate(self.hard, width / 2 + EDGE_CLEAR + P * 0.75) | self.keep
            res.append(b)
        via = dilate((self.owner[0] != -1) & (self.owner[0] != n) | (self.owner[1] != -1) & (self.owner[1] != n),
                     VIA_D / 2 + CLEAR + P * 0.75) | dilate(self.hard, VIA_D / 2 + EDGE_CLEAR + P * 0.75) | self.keep
        return res, via

    def astar(self, sources, targets, blocked, via_blocked, own):
        tgt = set(targets)
        tcoords = np.array([(i, j) for _, i, j in targets])

        def h(i, j):
            d = np.abs(tcoords - (i, j))
            dmin = d.min(axis=1), d.max(axis=1)
            return float(np.min(dmin[1] - dmin[0] + 1.4142 * dmin[0]))

        openq = []
        best = {}
        prev = {}
        for s in sources:
            key = (s, -1)
            best[key] = 0.0
            heapq.heappush(openq, (h(s[1], s[2]), 0.0, s, -1))
        tcache = {}
        while openq:
            f, g, s, d = heapq.heappop(openq)
            if best.get((s, d), 1e18) < g:
                continue
            if s in tgt:
                path = [s]
                k = (s, d)
                while k in prev:
                    k = prev[k]
                    path.append(k[0])
                return path[::-1]
            L, i, j = s
            for nd, (di, dj) in enumerate(DIRS):
                ni, nj = i + di, j + dj
                if not (0 <= ni < NX and 0 <= nj < NY):
                    continue
                if blocked[L][ni, nj] and not own[L][ni, nj]:
                    continue
                if di and dj and (blocked[L][ni, j] and not own[L][ni, j]) and (blocked[L][i, nj] and not own[L][i, nj]):
                    continue
                step = 1.4142 if di and dj else 1.0
                ng = g + step + (TURN_COST if d not in (-1, nd, 8) else 0.0)
                ns = (L, ni, nj)
                if ng < best.get((ns, nd), 1e18):
                    best[(ns, nd)] = ng
                    prev[(ns, nd)] = (s, d)
                    if ns not in tcache:
                        tcache[ns] = h(ni, nj)
                    heapq.heappush(openq, (ng + tcache[ns], ng, ns, nd))
            # Lagenwechsel per Via
            ns = (1 - L, i, j)
            if not via_blocked[i, j] or (own[0][i, j] and own[1][i, j]):
                ng = g + VIA_COST
                if ng < best.get((ns, 8), 1e18):
                    best[(ns, 8)] = ng
                    prev[(ns, 8)] = (s, d)
                    heapq.heappush(openq, (ng + h(i, j), ng, ns, 8))
        return None

    def mark(self, n, path, width):
        r = width / 2
        for L, i, j in path:
            for di, dj in disk(r / P):
                a, b = i + di, j + dj
                if 0 <= a < NX and 0 <= b < NY and self.owner[L][a, b] == -1:
                    self.owner[L][a, b] = n

    def route_net(self, name):
        n = self.nets[name]
        width = WIDTH.get(name, DEFAULT_W)
        pads = [p for p in self.pads if p[0] == n]
        if len(pads) < 2:
            return [], []
        blocked, via_blocked = self.blocked(n, width)
        own = [(self.owner[L] == n) for L in (0, 1)]
        # Reihenfolge: vom ersten Pad aus immer das naechste anschliessen
        tree_pads = [pads[0]]
        rest = pads[1:]
        tree_cells = [(L, i, j) for L in pads[0][1] for i, j in zip(*np.nonzero(pads[0][2]))]
        segments, vias = [], []
        while rest:
            tc = np.array([[i, j] for _, i, j in tree_cells])
            rest.sort(key=lambda p: np.min(np.abs(tc - cell(*p[3])).sum(axis=1)))
            pad = rest.pop(0)
            targets = [(L, i, j) for L in pad[1] for i, j in zip(*np.nonzero(pad[2]))]
            path = self.astar(tree_cells, targets, blocked, via_blocked, own)
            if path is None:
                raise RuntimeError(f"Netz {name}: keine Verbindung zu {pad[4].GetParentFootprint().GetReference()}.{pad[4].GetNumber()}")
            self.mark(n, path, width)
            for L, i, j in path:
                own[L][i, j] = True
            tree_cells += path
            tree_cells += targets
            segments.append((path, pad[3]))
            for a, b in zip(path, path[1:]):
                if a[0] != b[0]:
                    vias.append((a[1], a[2]))
            tree_pads.append(pad)
        # Via-Kupfer auf beiden Lagen eintragen
        for i, j in vias:
            for di, dj in disk(VIA_D / 2 / P):
                for L in (0, 1):
                    a, b = i + di, j + dj
                    if 0 <= a < NX and 0 <= b < NY and self.owner[L][a, b] == -1:
                        self.owner[L][a, b] = n
        return segments, vias


def simplify(pts):
    out = [pts[0]]
    for k in range(1, len(pts) - 1):
        a, b, c = out[-1], pts[k], pts[k + 1]
        if (b[0] - a[0]) * (c[1] - b[1]) != (b[1] - a[1]) * (c[0] - b[0]):
            out.append(b)
    out.append(pts[-1])
    return out


def main():
    path = os.path.join(ROOT, PROJECT + ".kicad_pcb")
    board = pcbnew.LoadBoard(path)
    for t in list(board.GetTracks()):
        board.Remove(t)
    r = Router(board)
    netobj = {name: board.FindNet(name) for name in r.nets}
    names = [nm for nm in r.nets if nm not in SKIP and not nm.startswith("unconnected")]
    # kurze Signalnetze zuerst, Versorgung zuletzt
    order = sorted(names, key=lambda nm: (nm in WIDTH, sum(1 for p in r.pads if p[0] == r.nets[nm])))
    ntr = nvia = 0
    for name in order:
        segs, vias = r.route_net(name)
        width = WIDTH.get(name, DEFAULT_W)
        for cells, _ in segs:
            # in Abschnitte gleicher Lage zerlegen
            run = [cells[0]]
            for c in cells[1:] + [None]:
                if c is not None and c[0] == run[-1][0]:
                    run.append(c)
                    continue
                pts = simplify([(i, j) for _, i, j in run])
                for (i0, j0), (i1, j1) in zip(pts, pts[1:]):
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(pcbnew.VECTOR2I_MM(float(OX + i0 * P), float(OY + j0 * P)))
                    t.SetEnd(pcbnew.VECTOR2I_MM(float(OX + i1 * P), float(OY + j1 * P)))
                    t.SetWidth(pcbnew.FromMM(width))
                    t.SetLayer(pcbnew.F_Cu if run[0][0] == 0 else pcbnew.B_Cu)
                    t.SetNet(netobj[name])
                    board.Add(t)
                    ntr += 1
                if c is not None:
                    run = [c]
        for i, j in vias:
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I_MM(float(OX + i * P), float(OY + j * P)))
            v.SetWidth(pcbnew.FromMM(VIA_D))
            v.SetDrill(pcbnew.FromMM(VIA_DRILL))
            v.SetNet(netobj[name])
            board.Add(v)
            nvia += 1
        print(f"  {name:12s} ok")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(path)
    print(f"{ntr} Leiterbahnsegmente, {nvia} Vias")


if __name__ == "__main__":
    main()
