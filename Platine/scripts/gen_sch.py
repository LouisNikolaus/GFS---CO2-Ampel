"""Erzeugt den Schaltplan CO2-Ampel.kicad_sch (KiCad 9)."""
import copy
import math
import os
import uuid

import sexpr
from sexpr import Q

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = "CO2-Ampel"
LOCAL_LIB = os.path.join(ROOT, "lib", "CO2.kicad_sym")
ROOT_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "co2-ampel-root"))

_n = 0


def uid():
    global _n
    _n += 1
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"co2-ampel-{_n}"))


def g(n):
    return round(n * 2.54, 4)


items = []          # Schaltplan-Elemente (Listen)
lib_symbols = {}    # lib_id -> Symbol-Definition
_pwr_count = [0]

DIRS = {"right": (1, 0), "left": (-1, 0), "up": (0, -1), "down": (0, 1)}
LABEL_ANGLE = {"right": 0, "up": 90, "left": 180, "down": 270}


def font(size=1.27, justify=None, hide=False):
    e = ["effects", ["font", ["size", size, size]]]
    if justify:
        e.append(["justify"] + justify.split())
    if hide:
        e.append(["hide", "yes"])
    return e


def rot(x, y, deg):
    a = math.radians(deg)
    return (round(x * math.cos(a) - y * math.sin(a), 4), round(x * math.sin(a) + y * math.cos(a), 4))


class Part:
    def __init__(self, ref, lib_id, x, y, angle=0, value=None, footprint=None, in_bom=True, fields=None):
        if lib_id not in lib_symbols:
            libpath = LOCAL_LIB if lib_id.startswith("CO2:") else None
            lib_symbols[lib_id] = sexpr.get_symbol(lib_id, libpath)
        sym = lib_symbols[lib_id]
        self.x, self.y, self.angle = x, y, angle
        self.pins = sexpr.pins(sym)
        props = {p[1]: p for p in sexpr.find(sym, "property")}
        is_power = ref.startswith("#")
        node = ["symbol", ["lib_id", Q(lib_id)], ["at", x, y, angle], ["unit", 1],
                ["exclude_from_sim", "no"], ["in_bom", "yes" if in_bom and not is_power else "no"],
                ["on_board", "no" if is_power else "yes"], ["dnp", "no"], ["uuid", Q(uid())]]
        vals = {"Reference": ref,
                "Value": value if value is not None else str(props["Value"][2]),
                "Footprint": footprint if footprint is not None else str(props["Footprint"][2]),
                "Datasheet": str(props["Datasheet"][2]) if "Datasheet" in props else "",
                "Description": str(props["Description"][2]) if "Description" in props else ""}
        vals.update(fields or {})
        for k, v in vals.items():
            lp = props.get(k)
            if lp is not None:
                at = sexpr.find1(lp, "at")
                dx, dy = rot(float(at[1]), float(at[2]), angle)
                pangle = float(at[3])
                eff = copy.deepcopy(sexpr.find1(lp, "effects"))
            else:
                dx, dy, pangle, eff = 0, 0, 0, font(hide=True)
            if k in ("Footprint", "Datasheet", "Description") or (is_power and k == "Reference"):
                eff = [e for e in eff if not (isinstance(e, list) and e[0] == "hide")] + [["hide", "yes"]]
            node.append(["property", Q(k), Q(v), ["at", round(x + dx, 4), round(y - dy, 4), pangle], eff])
        for num in self.pins:
            node.append(["pin", Q(num), ["uuid", Q(uid())]])
        node.append(["instances", ["project", Q(PROJECT),
                                   ["path", Q("/" + ROOT_UUID), ["reference", Q(ref)], ["unit", 1]]]])
        items.append(node)

    def pin(self, num):
        px, py, prot, _, _ = self.pins[str(num)]
        dx, dy = rot(px, py, self.angle)
        a = (prot + 180 + self.angle) % 360   # Richtung vom Pin-Ende nach aussen (Y oben)
        out = {0: "right", 90: "up", 180: "left", 270: "down"}[round(a) % 360]
        return (round(self.x + dx, 4), round(self.y - dy, 4), out)


def wire(*pts):
    for a, b in zip(pts, pts[1:]):
        items.append(["wire", ["pts", ["xy", a[0], a[1]], ["xy", b[0], b[1]]],
                      ["stroke", ["width", 0], ["type", "default"]], ["uuid", Q(uid())]])


def stub(pin, length=2.54, direction=None):
    x, y, d = pin
    d = direction or d
    vx, vy = DIRS[d]
    end = (round(x + vx * length, 4), round(y + vy * length, 4))
    wire((x, y), end)
    return end, d


def label(pin, name, length=2.54):
    (x, y), d = stub(pin, length)
    ang = LABEL_ANGLE[d]
    just = "left bottom" if ang in (0, 90) else "right bottom"
    items.append(["label", Q(name), ["at", x, y, ang], font(justify=just), ["uuid", Q(uid())]])


def power(pin, name, body=None, length=2.54):
    """Versorgungssymbol an Pin anschliessen. body = Richtung, in die das Symbol zeigt."""
    (x, y), d = stub(pin, length)
    if body is None:
        body = d
    if name == "GND":
        ang = {"down": 0, "right": 90, "up": 180, "left": 270}[body]
    else:
        ang = {"up": 0, "left": 90, "down": 180, "right": 270}[body]
    _pwr_count[0] += 1
    Part(f"#PWR{_pwr_count[0]:02d}", "power:" + name, x, y, ang)
    return (x, y)


def noconn(pin):
    items.append(["no_connect", ["at", pin[0], pin[1]], ["uuid", Q(uid())]])


def text(s, x, y, size=1.27):
    items.append(["text", Q(s), ["exclude_from_sim", "no"], ["at", x, y, 0],
                  font(size, "left top"), ["uuid", Q(uid())]])


FP_R = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
FP_SOCK4 = "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical"

# ---------------------------------------------------------------- D1 mini
U1 = Part("U1", "CO2:WeMos_D1_mini", g(30), g(40), value="D1 mini (ESP8266)")
power(U1.pin(9), "+5V", body="up")
power(U1.pin(8), "+3V3", body="left")
for p in (1, 2, 16, 15, 3, 11):
    noconn(U1.pin(p)[:2])
label(U1.pin(14), "SCL")
label(U1.pin(13), "SDA")
label(U1.pin(12), "TASTER")
label(U1.pin(4), "LED_ROT")
label(U1.pin(5), "LED_GELB")
label(U1.pin(6), "LED_GRUEN")
label(U1.pin(7), "BUZZER")
gx, gy, _ = U1.pin(10)
wire((gx, gy), (gx, gy + 2.54), (gx + 5.08, gy + 2.54))
Part("#PWR_FLAG1", "power:PWR_FLAG", gx + 5.08, gy + 2.54, value="PWR_FLAG")
power((gx, gy + 2.54, "down"), "GND")
text("Stromversorgung ueber die USB-Buchse des D1 mini.\n"
     "5V = USB-Spannung, 3V3 = Regler auf dem D1 mini (max. ca. 500 mA)", g(14), g(66))

# ---------------------------------------------------------------- I2C Pull-ups (optional)
R1 = Part("R1", "Device:R", g(52), g(16), value="4k7 (opt.)", footprint=FP_R)
R2 = Part("R2", "Device:R", g(57), g(16), value="4k7 (opt.)", footprint=FP_R)
power(R1.pin(1), "+3V3")
power(R2.pin(1), "+3V3")
label(R1.pin(2), "SCL")
label(R2.pin(2), "SDA")
text("I2C-Pull-ups: nur bestuecken, wenn weder\nDisplay noch Sensor eigene Pull-ups haben.", g(49), g(24))

# ---------------------------------------------------------------- OLED
J1 = Part("J1", "Connector_Generic:Conn_01x04", g(80), g(16), value="OLED 0,96\" SSD1306", footprint=FP_SOCK4)
power(J1.pin(1), "GND", body="left", length=7.62)
power(J1.pin(2), "+3V3", body="left")
label(J1.pin(3), "SCL")
label(J1.pin(4), "SDA")
text("OLED-Display 128x64, I2C (Adresse 0x3C)\nPinfolge GND-VCC-SCL-SDA vor Bestellung pruefen!", g(72), g(21))

# ---------------------------------------------------------------- CO2-Sensor
J2 = Part("J2", "Connector_Generic:Conn_01x04", g(80), g(34), value="CO2-Sensor I2C", footprint=FP_SOCK4)
label(J2.pin(1), "SENS_VCC")
power(J2.pin(2), "GND", body="left", length=7.62)
label(J2.pin(3), "SCL")
label(J2.pin(4), "SDA")
text("CO2-Sensor (z.B. SCD40/SCD41/SCD30), I2C\nPinfolge VCC-GND-SCL-SDA an Sensormodul anpassen!", g(72), g(39))

JP1 = Part("JP1", "Jumper:SolderJumper_3_Bridged12", g(56), g(34), value="3V3 | 5V",
           footprint="Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm_NumberLabels", in_bom=False)
power(JP1.pin(1), "+3V3", body="up")
power(JP1.pin(3), "+5V", body="up")
label(JP1.pin(2), "SENS_VCC")
C1 = Part("C1", "Device:C_Polarized", g(66), g(36), value="100uF",
          footprint="Capacitor_THT:CP_Radial_D6.3mm_P2.50mm")
label(C1.pin(1), "SENS_VCC")
power(C1.pin(2), "GND")
text("JP1: Sensor-Versorgung waehlen\n1-2 = 3,3 V (Standard), 2-3 = 5 V", g(49), g(41))

# ---------------------------------------------------------------- LED-Ampel
for i, (net, col, ref_r, ref_d) in enumerate([("LED_ROT", "rot", "R3", "D1"),
                                               ("LED_GELB", "gelb", "R4", "D2"),
                                               ("LED_GRUEN", "gruen", "R5", "D3")]):
    y = g(50 + 5 * i)
    R = Part(ref_r, "Device:R", g(55), y, angle=90, value="220", footprint=FP_R)
    D = Part(ref_d, "Device:LED", g(61), y, angle=180, value=f"LED 5mm {col}",
             footprint="LED_THT:LED_D5.0mm")
    label(R.pin(1), net)
    wire(R.pin(2)[:2], D.pin(2)[:2])
    power(D.pin(1), "GND", body="down")
text("CO2-Ampel: gruen < 1000 ppm, gelb < 1500 ppm, rot >= 1500 ppm", g(49), g(64))

# ---------------------------------------------------------------- Summer
R6 = Part("R6", "Device:R", g(84), g(55), angle=90, value="1k", footprint=FP_R)
Q1 = Part("Q1", "Transistor_BJT:BC547", g(84) + 3.81 + 5.08 + 1.27, g(55), value="BC547")
label(R6.pin(1), "BUZZER")
wire(R6.pin(2)[:2], Q1.pin(2)[:2])
power(Q1.pin(3), "GND", body="down")
label(Q1.pin(1), "BUZ_N")
BZ1 = Part("BZ1", "Device:Buzzer", g(100), g(48), value="Summer 5V aktiv",
           footprint="Buzzer_Beeper:Buzzer_12x9.5RM7.6")
power(BZ1.pin(1), "+5V", body="up")
label(BZ1.pin(2), "BUZ_N")
D4 = Part("D4", "Diode:1N4148", g(92), g(48), angle=90, value="1N4148")
power(D4.pin(1), "+5V", body="up")
label(D4.pin(2), "BUZ_N")
text("Aktiver 5V-Summer (12 mm), geschaltet ueber Q1.\nD4 = Freilaufdiode", g(80), g(62))

# ---------------------------------------------------------------- Taster
SW1 = Part("SW1", "Switch:SW_Push", g(22), g(57), value="Taster",
           footprint="Button_Switch_THT:SW_PUSH_6mm_H13mm")
label(SW1.pin(1), "TASTER")
power(SW1.pin(2), "GND", body="down")
text("Taster an D3/GPIO0 (interner Pull-up).\nBeim Einschalten nicht druecken (Flash-Modus).", g(14), g(60))

# ---------------------------------------------------------------- Befestigung
for i in range(4):
    Part(f"H{i + 1}", "Mechanical:MountingHole", g(46 + 6 * i), g(70), value="M3",
         footprint="MountingHole:MountingHole_3.2mm_M3", in_bom=False)

text("CO2-Ampel mit Wemos D1 mini (ESP8266)\n"
     "- CO2 + Temperatur + Luftfeuchte ueber I2C-Sensor\n"
     "- Anzeige auf OLED, Ampel-LEDs, Summer, Taster\n"
     "- WLAN ueber ESP8266", g(8), g(6), size=1.8)

# ---------------------------------------------------------------- Datei schreiben
sch = ["kicad_sch", ["version", 20250114], ["generator", Q("eeschema")], ["generator_version", Q("9.0")],
       ["uuid", Q(ROOT_UUID)], ["paper", Q("A4")],
       ["title_block", ["title", Q("CO2-Ampel mit D1 mini")], ["date", Q("2026-09-29")],
        ["rev", Q("0.1")], ["comment", 1, Q("ESP8266 + CO2-Sensor (I2C) + OLED + Ampel-LEDs")]],
       ["lib_symbols"] + list(lib_symbols.values())]
sch += items
sch += [["sheet_instances", ["path", Q("/"), ["page", Q("1")]]], ["embedded_fonts", "no"]]

with open(os.path.join(ROOT, PROJECT + ".kicad_sch"), "w", encoding="utf-8") as f:
    f.write(sexpr.dump(sch) + "\n")
print("Schaltplan geschrieben:", len(items), "Elemente")
