"""Erzeugt CO2-Ampel.kicad_pcb aus der Netzliste (mit KiCad-Python ausfuehren:
"C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" Platine\\scripts\\gen_pcb.py)"""
import json
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sexpr  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPDIR = os.path.join(sexpr.KICAD, "share", "kicad", "footprints")
PROJECT = "CO2-Ampel"

# Platinenmasse (mm) – Ursprung links oben, auf dem Blatt um OX/OY verschoben
W, H, R_CORNER = 100.0, 60.0, 3.0
OX, OY = 50.0, 50.0
HOLES = [(4, 4), (96, 4), (4, 56), (96, 56)]
SLOT_X, SLOT_Y0, SLOT_Y1, SLOT_W = 70.0, 9.0, 51.0, 2.0   # Waermeschlitz Sensor/ESP

# Referenz -> (x, y, Drehung) = Position des Footprint-Ursprungs
PLACEMENT = {
    "U1": (25.8, 18.57, -90),      # USB zeigt nach links an die Platinenkante
    "J1": (48.19, 6.0, 90),        # OLED-Buchse, Pin 1 (GND) links
    "J2": (81.19, 10.0, 90),       # Sensor-Buchse
    "JP1": (78.0, 46.0, 0),
    "C1": (86.0, 46.0, 0),
    "R1": (10.0, 8.0, 0),
    "R2": (10.0, 12.0, 0),
    "D1": (41.0 - 1.27, 44.0, 0),
    "D2": (51.0 - 1.27, 44.0, 0),
    "D3": (61.0 - 1.27, 44.0, 0),
    "R3": (46.0, 55.0, 90),
    "R4": (56.0, 55.0, 90),
    "R5": (66.0, 55.0, 90),
    "BZ1": (8.2, 50.0, 0),
    "Q1": (20.5, 50.0, 0),
    "R6": (18.0, 56.5, 0),
    "D4": (20.0, 45.0, 0),
    "SW1": (26.75, 48.75, 0),
    "H1": (4, 4, 0), "H2": (96, 4, 0), "H3": (4, 56, 0), "H4": (96, 56, 0),
}

# Positionen der Referenz-Beschriftungen (Platinenkoordinaten)
REF_POS = {"BZ1": (12.0, 46.3), "D4": (30.0, 45.0), "Q1": (22.0, 53.6), "R6": (28.8, 56.5), "R2": (21.0, 12.0),
           "R1": (21.0, 8.0)}

SILK_TEXT = [
    ("CO2-Ampel v0.1", 85.0, 55.0, 1.5),
    ("OLED", 52.0, 2.2, 1.0),
    ("CO2-Sensor", 85.0, 6.5, 1.0),
    ("rot", 41.0, 48.5, 1.0),
    ("gelb", 51.0, 48.5, 1.0),
    ("gruen", 61.0, 48.5, 1.0),
    ("3V3 | 5V", 79.3, 49.0, 0.8),
]


def mm(x, y):
    return pcbnew.VECTOR2I_MM(OX + x, OY + y)


def load_netlist():
    tree = sexpr.parse(open(os.path.join(ROOT, PROJECT + ".net"), encoding="utf-8").read())
    comps = {}
    for c in sexpr.find(sexpr.find1(tree, "components"), "comp"):
        ref = str(sexpr.find1(c, "ref")[1])
        comps[ref] = {
            "value": str(sexpr.find1(c, "value")[1]),
            "footprint": str(sexpr.find1(c, "footprint")[1]),
            "tstamp": str(sexpr.find1(c, "tstamps")[1]),
            "Datasheet": str((sexpr.find1(c, "datasheet") or [0, ""])[1]),
            "Description": str((sexpr.find1(c, "description") or [0, ""])[1]),
        }
    nets = {}
    for n in sexpr.find(sexpr.find1(tree, "nets"), "net"):
        name = str(sexpr.find1(n, "name")[1])
        nets[name] = [(str(sexpr.find1(x, "ref")[1]), str(sexpr.find1(x, "pin")[1]))
                      for x in sexpr.find(n, "node")]
    return comps, nets


def add_shape(board, layer, shape, pts, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(shape)
    s.SetLayer(layer)
    s.SetWidth(pcbnew.FromMM(width))
    if shape == pcbnew.SHAPE_T_SEGMENT:
        s.SetStart(mm(*pts[0]))
        s.SetEnd(mm(*pts[1]))
    elif shape == pcbnew.SHAPE_T_ARC:
        s.SetArcGeometry(mm(*pts[0]), mm(*pts[1]), mm(*pts[2]))
    board.Add(s)


def outline(board):
    r = R_CORNER
    L = pcbnew.Edge_Cuts
    seg = pcbnew.SHAPE_T_SEGMENT
    arc = pcbnew.SHAPE_T_ARC
    k = r * (1 - math.sqrt(0.5))
    add_shape(board, L, seg, [(r, 0), (W - r, 0)])
    add_shape(board, L, seg, [(W, r), (W, H - r)])
    add_shape(board, L, seg, [(W - r, H), (r, H)])
    add_shape(board, L, seg, [(0, H - r), (0, r)])
    add_shape(board, L, arc, [(W - r, 0), (W - k, k), (W, r)])
    add_shape(board, L, arc, [(W, H - r), (W - k, H - k), (W - r, H)])
    add_shape(board, L, arc, [(r, H), (k, H - k), (0, H - r)])
    add_shape(board, L, arc, [(0, r), (k, k), (r, 0)])
    # Schlitz zur thermischen Entkopplung des Sensors vom ESP8266
    h = SLOT_W / 2
    add_shape(board, L, seg, [(SLOT_X - h, SLOT_Y0), (SLOT_X - h, SLOT_Y1)])
    add_shape(board, L, seg, [(SLOT_X + h, SLOT_Y0), (SLOT_X + h, SLOT_Y1)])
    add_shape(board, L, arc, [(SLOT_X - h, SLOT_Y0), (SLOT_X, SLOT_Y0 - h), (SLOT_X + h, SLOT_Y0)])
    add_shape(board, L, arc, [(SLOT_X - h, SLOT_Y1), (SLOT_X, SLOT_Y1 + h), (SLOT_X + h, SLOT_Y1)])


def add_zone(board, layer, net, corners, rule_area=False):
    z = pcbnew.ZONE(board)
    if layer is not None:
        z.SetLayer(layer)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in corners:
        ol.Append(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))
    if rule_area:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        ls = pcbnew.LSET()
        ls.AddLayer(pcbnew.F_Cu)
        ls.AddLayer(pcbnew.B_Cu)
        z.SetLayerSet(ls)
        z.SetZoneName("Keine Kupferflaeche unter WLAN-Antenne")
    else:
        z.SetNet(net)
        z.SetLocalClearance(pcbnew.FromMM(0.3))
        z.SetMinThickness(pcbnew.FromMM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetZoneName("GND")
    board.Add(z)


def set_netclasses():
    path = os.path.join(ROOT, PROJECT + ".kicad_pro")
    pro = json.load(open(path, encoding="utf-8"))
    base = {"bus_width": 12, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2,
            "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1, "pcb_color": "rgba(0, 0, 0, 0.000)",
            "priority": 2147483647, "schematic_color": "rgba(0, 0, 0, 0.000)", "via_diameter": 0.8,
            "via_drill": 0.4, "wire_width": 6}
    pro["net_settings"] = {
        "classes": [dict(base, name="Default", clearance=0.3, track_width=0.3),
                    dict(base, name="Power", clearance=0.3, track_width=0.5, priority=0)],
        "meta": {"version": 4},
        "net_colors": None,
        "netclass_assignments": None,
        "netclass_patterns": [{"netclass": "Power", "pattern": p}
                              for p in ("GND", "+5V", "+3V3")],
    }
    json.dump(pro, open(path, "w", encoding="utf-8"), indent=2)


def main():
    set_netclasses()
    comps, nets = load_netlist()
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(pcbnew.FromMM(1.6))

    tb = board.GetTitleBlock()
    tb.SetTitle("CO2-Ampel mit D1 mini")
    tb.SetRevision("0.1")
    tb.SetDate("2026-09-29")

    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni

    fps = {}
    for ref, c in comps.items():
        lib, name = c["footprint"].split(":")
        libdir = os.path.join(ROOT, "lib", "CO2.pretty") if lib == "CO2" else os.path.join(FPDIR, lib + ".pretty")
        fp = pcbnew.FootprintLoad(libdir, name)
        if fp is None:
            raise RuntimeError(f"Footprint nicht gefunden: {c['footprint']}")
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + c["tstamp"]))
        fp.SetSheetname("/")
        fp.SetSheetfile(PROJECT + ".kicad_sch")
        for field in ("Datasheet", "Description"):
            fp.SetField(field, c[field])
        if ref.startswith("H"):
            fp.SetExcludedFromBOM(True)
            fp.Reference().SetVisible(False)
        x, y, rot = PLACEMENT[ref]
        board.Add(fp)
        fp.SetPosition(mm(x, y))
        fp.SetOrientationDegrees(rot)
        if ref in REF_POS:
            fp.Reference().SetPosition(mm(*REF_POS[ref]))
            fp.Reference().SetTextAngleDegrees(0)
        fps[ref] = fp

    for name, nodes in nets.items():
        for ref, pin in nodes:
            for pad in fps[ref].Pads():
                if pad.GetNumber() == pin:
                    pad.SetNet(netinfo[name])
                    if name == "GND" and ref in ("J1", "J2"):
                        pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

    outline(board)

    for txt, x, y, size in SILK_TEXT:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetPosition(mm(x, y))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I_MM(size, size))
        t.SetTextThickness(pcbnew.FromMM(size * 0.15))
        board.Add(t)

    gnd = netinfo["GND"]
    rect = [(0, 0), (W, 0), (W, H), (0, H)]
    add_zone(board, pcbnew.F_Cu, gnd, rect)
    add_zone(board, pcbnew.B_Cu, gnd, rect)
    # Antennenbereich des ESP-12F (rechtes Ende des D1 mini) frei von Kupferflaechen halten
    add_zone(board, None, None, [(25.5, 15.5), (36.5, 15.5), (36.5, 44.5), (25.5, 44.5)], rule_area=True)

    out = os.path.join(ROOT, PROJECT + ".kicad_pcb")
    board.Save(out)
    print("Platine gespeichert:", out)


if __name__ == "__main__":
    main()
