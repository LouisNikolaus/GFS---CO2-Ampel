"""3D-Druck-Gehaeuse fuer die CO2-Ampel (Unterschale + Deckel) als STL.
Ausfuehren mit normalem Python:  pip install manifold3d numpy ;  python gehaeuse/scripts/gen_case.py

Koordinaten: x wie in KiCad, y = 60 - y_KiCad (Draufsicht wie im PCB-Editor), z nach oben.
Alle Masse in mm. Hoehen der gesteckten Module unbedingt vor dem Druck nachmessen!"""
import os

import numpy as np
from manifold3d import CrossSection, JoinType, Manifold

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = ROOT

# ------------------------------------------------------------------ Parameter
PCB_W, PCB_H, PCB_T, PCB_R = 100.0, 60.0, 1.6, 3.0
HOLES = [(4, 4), (96, 4), (4, 56), (96, 56)]       # KiCad-Koordinaten
GAP = 0.5            # Luft Platine <-> Innenwand
WALL = 2.0
FLOOR = 2.0
STANDOFF_H = 5.0     # Platz fuer Loetstellen unter der Platine
STANDOFF_D = 7.0
SCREW_HOLE_D = 2.6   # M3 selbstschneidend in PLA/PETG (Einschmelzmutter: 4.0)
PARTS_H = 16.0       # hoechstes Bauteil ueber Platinenoberseite (D1 mini auf Buchsenleiste)
LID_T = 2.0
LIP_H, LIP_T, LIP_CLEAR = 3.0, 1.5, 0.15
SEG = 64

Z_PCB_BOT = FLOOR + STANDOFF_H
Z_PCB_TOP = Z_PCB_BOT + PCB_T
Z_LID = Z_PCB_TOP + PARTS_H          # Unterseite Deckel = Oberkante Unterschale

# Bauteilpositionen (KiCad-Koordinaten der Platine)
USB_Y, USB_W, USB_Z0 = 30.0, 12.5, Z_PCB_TOP + 8.0   # Micro-USB des D1 mini (links)
OLED_WIN = (52.0, 17.2, 25.0, 14.0)                  # Mitte x, Mitte y, Breite, Hoehe
LEDS = [(41, 44), (51, 44), (61, 44)]
LED_D = 5.3
BUTTON = (30.0, 51.0)
BUTTON_TOP = Z_PCB_TOP + 13.0                        # Taster 6x6 mm, H = 13 mm
BUZZER = (12.0, 50.0)
SLOT_X = 70.0                                        # Trennwand Sensor | ESP
SENSOR_AREA = (73.0, 8.0, 97.0, 40.0)                # x0, y0, x1, y1


def ky(y):
    """KiCad-y -> Gehaeuse-y"""
    return PCB_H - y


def rrect(x0, y0, x1, y1, r):
    w, h = x1 - x0, y1 - y0
    cs = CrossSection.square([w - 2 * r, h - 2 * r]).translate([x0 + r, y0 + r])
    return cs.offset(r, JoinType.Round, circular_segments=SEG) if r > 0 else cs


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl(x, y, z0, z1, d):
    return Manifold.cylinder(z1 - z0, d / 2, d / 2, SEG).translate([x, y, z0])


def extrude(cs, z0, z1):
    return cs.extrude(z1 - z0).translate([0, 0, z0])


# Innenraum / Aussenkontur
IX0, IY0, IX1, IY1 = -GAP, -GAP, PCB_W + GAP, PCB_H + GAP
IR = PCB_R + GAP
OX0, OY0, OX1, OY1 = IX0 - WALL, IY0 - WALL, IX1 + WALL, IY1 + WALL
OR = IR + WALL


def bottom():
    shell = extrude(rrect(OX0, OY0, OX1, OY1, OR), 0, Z_LID)
    shell -= extrude(rrect(IX0, IY0, IX1, IY1, IR), FLOOR, Z_LID + 1)
    # Abstandshalter mit Schraubloch
    for hx, hy in HOLES:
        shell += cyl(hx, ky(hy), FLOOR - 0.01, Z_PCB_BOT, STANDOFF_D)
        shell -= cyl(hx, ky(hy), FLOOR + 0.6, Z_PCB_BOT + 1, SCREW_HOLE_D)
    # USB-Aussparung links (oben offen, D1 mini wird von oben eingesetzt)
    shell -= box(OX0 - 1, ky(USB_Y) - USB_W / 2, USB_Z0, IX0 + 0.5, ky(USB_Y) + USB_W / 2, Z_LID + 1)
    # Lueftung Sensorkammer: Schlitze rechte Wand (unten + oben -> Kamineffekt)
    for i in range(7):
        y = ky(10 + i * 6.5)
        for z0, z1 in ((Z_PCB_BOT - 3.5, Z_PCB_BOT - 0.5), (Z_PCB_TOP + 4, Z_PCB_TOP + 10)):
            shell -= box(IX1 - 1, y - 1.0, z0, OX1 + 1, y + 1.0, z1)
    # Lueftung ESP-Bereich: Schlitze Rueckwand (y = 0 in KiCad = hinten)
    for i in range(6):
        x = 8 + i * 5
        shell -= box(x - 1.0, IY1 - 1, Z_PCB_TOP + 4, x + 1.0, OY1 + 1, Z_PCB_TOP + 12)
    # Bodenschlitze unter der Sensorkammer (Frischluft von unten)
    x0, y0, x1, y1 = SENSOR_AREA
    for i in range(6):
        x = x0 + 2 + i * 4
        shell -= box(x - 1.0, ky(50), -1, x + 1.0, ky(12), FLOOR + 1)
    # Schluessellochaufhaengung fuer Wandmontage
    for kx in (30.0, 60.0):
        kyy = ky(16)
        shell -= cyl(kx, kyy, -1, FLOOR + 1, 8.0)
        shell -= box(kx - 2.1, kyy, -1, kx + 2.1, kyy + 7, FLOOR + 1)   # Schlitz nach oben
    return shell


def lid():
    z0, z1 = Z_LID, Z_LID + LID_T
    top = extrude(rrect(OX0, OY0, OX1, OY1, OR), z0, z1)
    # Steckrand (Lippe), passt innen in die Unterschale
    c = LIP_CLEAR
    lip = extrude(rrect(IX0 + c, IY0 + c, IX1 - c, IY1 - c, IR - c), z0 - LIP_H, z0)
    lip -= extrude(rrect(IX0 + c + LIP_T, IY0 + c + LIP_T, IX1 - c - LIP_T, IY1 - c - LIP_T, IR - c - LIP_T),
                   z0 - LIP_H - 1, z0 + 0.01)
    # Lippe links unterbrechen (D1 mini + USB-Stecker)
    lip -= box(IX0 - 1, ky(46), z0 - LIP_H - 1, IX0 + 4, ky(14), z0 + 0.01)
    lid = top + lip
    # USB-Aussparung: Deckel fuellt die Kerbe der Unterschale nicht, nur oben abschliessen
    # Trennwand ueber dem Platinenschlitz (thermische Trennung Sensor / ESP)
    lid += box(SLOT_X - 0.8, ky(PCB_H - 1), Z_PCB_TOP + 1.5, SLOT_X + 0.8, ky(1), z0 + 0.01)
    # Display-Fenster mit Fase
    cx, cy, w, h = OLED_WIN
    cy = ky(cy)
    lid -= box(cx - w / 2, cy - h / 2, z0 - 1, cx + w / 2, cy + h / 2, z1 + 1)
    lid -= Manifold.batch_hull([
        Manifold.cube([w, h, 0.01], center=True).translate([cx, cy, z0 + 0.8]),
        Manifold.cube([w + 2.4, h + 2.4, 0.01], center=True).translate([cx, cy, z1 + 0.01])])
    # LED-Loecher
    for x, y in LEDS:
        lid -= cyl(x, ky(y), z0 - 1, z1 + 1, LED_D)
    # Summer-Schallloecher
    bx, by = BUZZER[0], ky(BUZZER[1])
    for dx, dy in [(0, 0), (3.5, 0), (-3.5, 0), (0, 3.5), (0, -3.5)]:
        lid -= cyl(bx + dx, by + dy, z0 - 1, z1 + 1, 2.0)
    # Taster: federnde Zunge mit Stoessel
    tx, ty = BUTTON[0], ky(BUTTON[1])
    tw, t_hinge, t_free = 9.0, ky(44.0), ky(56.0)
    s = 1.0
    zunge = box(tx - tw / 2 - s, t_free - s, z0 - 1, tx + tw / 2 + s, t_hinge, z1 + 1) - \
        box(tx - tw / 2, t_free, z0 - 2, tx + tw / 2, t_hinge + 1, z1 + 2)
    lid -= zunge
    lid += cyl(tx, ty, BUTTON_TOP + 0.4, z0 + 0.01, 4.0)
    # Zunge duenner machen -> weicher
    lid -= box(tx - tw / 2, t_free, z0 - 0.01, tx + tw / 2, t_hinge - 2.0, z0 + 0.8)
    lid += cyl(tx, ty, BUTTON_TOP + 0.4, z0 + 0.8, 4.0)
    # Lueftungsschlitze ueber dem Sensor
    x0, y0, x1, y1 = SENSOR_AREA
    for i in range(6):
        x = x0 + 2 + i * 4
        lid -= box(x - 0.9, ky(y1), z0 - 1, x + 0.9, ky(y0), z1 + 1)
    return lid


def write_stl(m, path):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(np.float32)
    t = np.asarray(mesh.tri_verts)
    tri = v[t]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    data = np.zeros(len(t), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    data["n"], data["v"] = n, tri
    with open(path, "wb") as f:
        f.write(b"CO2-Ampel Gehaeuse".ljust(80, b" "))
        f.write(np.uint32(len(t)).tobytes())
        f.write(data.tobytes())


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    b = bottom()
    L = lid()
    write_stl(b, os.path.join(OUT, "Unterschale.stl"))
    # Deckel fuer den Druck umdrehen (Oberseite aufs Druckbett)
    Lp = L.rotate([180, 0, 0]).translate([0, PCB_H, Z_LID + LID_T])
    write_stl(Lp, os.path.join(OUT, "Deckel.stl"))
    write_stl(b + L, os.path.join(OUT, "Zusammenbau_Vorschau.stl"))
    for name, m in (("Unterschale", b), ("Deckel (Druckposition)", Lp)):
        bb = m.bounding_box()
        print(f"{name}: {bb[3]-bb[0]:.1f} x {bb[4]-bb[1]:.1f} x {bb[5]-bb[2]:.1f} mm, "
              f"Volumen {m.volume()/1000:.1f} cm3, Genus {m.genus()}")
