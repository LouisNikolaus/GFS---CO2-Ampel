"""Erzeugt die Projektbibliothek: Symbol + Footprint fuer den Wemos/AZDelivery D1 mini."""
import os
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Nummer, Name, Seite, y-Position (Symbol), elektrischer Typ
# Nummerierung = Footprint-Pads: links 1..8 (RST..3V3, Antenne oben), rechts 9..16 (5V..TX)
D1_PINS = [
    (9, "5V", "L", 15.24, "power_out"),
    (8, "3V3", "L", 12.7, "power_out"),
    (1, "RST", "L", 7.62, "input"),
    (2, "A0", "L", 2.54, "input"),
    (16, "TX", "L", -5.08, "output"),
    (15, "RX", "L", -7.62, "input"),
    (3, "D0/GPIO16", "R", 15.24, "bidirectional"),
    (14, "D1/GPIO5/SCL", "R", 12.7, "bidirectional"),
    (13, "D2/GPIO4/SDA", "R", 10.16, "bidirectional"),
    (12, "D3/GPIO0", "R", 7.62, "bidirectional"),
    (11, "D4/GPIO2", "R", 5.08, "bidirectional"),
    (4, "D5/GPIO14", "R", 2.54, "bidirectional"),
    (5, "D6/GPIO12", "R", 0.0, "bidirectional"),
    (6, "D7/GPIO13", "R", -2.54, "bidirectional"),
    (7, "D8/GPIO15", "R", -5.08, "bidirectional"),
    (10, "GND", "B", 0.0, "power_in"),
]


def font(size=1.27, hide=False):
    return f'(effects (font (size {size} {size})){" (hide yes)" if hide else ""})'


def symbol_lib():
    pins = []
    for num, name, side, y, typ in D1_PINS:
        if side == "L":
            at = f"-15.24 {y} 0"
        elif side == "R":
            at = f"15.24 {y} 180"
        else:
            at = "0 -22.86 90"
        pins.append(
            f'(pin {typ} line (at {at}) (length 5.08) (name "{name}" {font()}) (number "{num}" {font()}))'
        )
    return f"""(kicad_symbol_lib (version 20241209) (generator "claude_gen") (generator_version "9.0")
  (symbol "WeMos_D1_mini" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)
    (property "Reference" "U" (at -10.16 19.05 0) {font()})
    (property "Value" "WeMos_D1_mini" (at 5.08 19.05 0) {font()})
    (property "Footprint" "CO2:WEMOS_D1_mini" (at 0 -26.67 0) {font(hide=True)})
    (property "Datasheet" "https://www.wemos.cc/en/latest/d1/d1_mini.html" (at 0 0 0) {font(hide=True)})
    (property "Description" "ESP8266 Modul D1 mini (AZDelivery / Wemos), steckbar" (at 0 0 0) {font(hide=True)})
    (symbol "WeMos_D1_mini_0_1"
      (rectangle (start -10.16 17.78) (end 10.16 -17.78) (stroke (width 0.254) (type default)) (fill (type background)))
    )
    (symbol "WeMos_D1_mini_1_1"
      {chr(10).join('      ' + p for p in pins)}
    )
  )
)
"""


def u():
    return str(uuid.uuid4())


def footprint():
    # Ursprung = Pad 1 (RST). Reihenabstand 22,86 mm (0.9"), Antenne oben (-y), USB unten (+y)
    x0, x1, y0, y1 = -1.37, 24.23, -8.9, 25.3
    items = []

    def line(a, b, layer, w):
        items.append(
            f'(fp_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width {w}) (type solid)) (layer "{layer}") (uuid "{u()}"))'
        )

    def rect(a, b, layer, w):
        items.append(
            f'(fp_rect (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width {w}) (type solid)) (fill no) (layer "{layer}") (uuid "{u()}"))'
        )

    def text(t, x, y, layer, size=1.0):
        items.append(
            f'(fp_text user "{t}" (at {x} {y} 0) (layer "{layer}") (uuid "{u()}") (effects (font (size {size} {size}) (thickness 0.15))))'
        )

    rect((x0, y0), (x1, y1), "F.SilkS", 0.12)
    rect((x0, y0), (x1, y1), "F.Fab", 0.1)
    rect((x0 - 0.5, y0 - 0.5), (x1 + 0.5, y1 + 2.0), "F.CrtYd", 0.05)
    # USB-Buchse (ragt ca. 1 mm ueber)
    rect((11.43 - 4.0, y1 - 5.0), (11.43 + 4.0, y1 + 1.0), "F.SilkS", 0.12)
    text("USB", 11.43, y1 - 2.5, "F.SilkS")
    text("ESP8266 Antenne", 11.43, y0 + 3.0, "F.SilkS")
    names_l = ["RST", "A0", "D0", "D5", "D6", "D7", "D8", "3V3"]
    names_r = ["TX", "RX", "D1", "D2", "D3", "D4", "G", "5V"]
    for i, n in enumerate(names_l):
        text(n, 2.8, i * 2.54, "F.SilkS", 0.8)
    for i, n in enumerate(names_r):
        text(n, 22.86 - 2.6, i * 2.54, "F.SilkS", 0.8)

    pads = []
    for i in range(8):
        shape = "rect" if i == 0 else "circle"
        pads.append((str(i + 1), shape, 0.0, i * 2.54))
        pads.append((str(16 - i), "circle", 22.86, i * 2.54))
    padtxt = [
        f'(pad "{n}" thru_hole {s} (at {x} {y}) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask") (remove_unused_layers no) (uuid "{u()}"))'
        for n, s, x, y in pads
    ]
    return f"""(footprint "WEMOS_D1_mini" (version 20241229) (generator "claude_gen") (generator_version "9.0") (layer "F.Cu")
  (descr "Wemos / AZDelivery D1 mini (ESP8266), 2x8 Buchsenleisten 2,54 mm, Reihenabstand 22,86 mm")
  (tags "ESP8266 D1 mini Wemos")
  (property "Reference" "REF**" (at 11.43 {y0 - 1.5} 0) (layer "F.SilkS") (uuid "{u()}") (effects (font (size 1 1) (thickness 0.15))))
  (property "Value" "WeMos_D1_mini" (at 11.43 {y1 + 3.5} 0) (layer "F.Fab") (uuid "{u()}") (effects (font (size 1 1) (thickness 0.15))))
  (attr through_hole)
  {chr(10).join('  ' + i for i in items)}
  {chr(10).join('  ' + p for p in padtxt)}
  (embedded_fonts no)
)
"""


if __name__ == "__main__":
    lib = os.path.join(ROOT, "lib")
    os.makedirs(os.path.join(lib, "CO2.pretty"), exist_ok=True)
    with open(os.path.join(lib, "CO2.kicad_sym"), "w", encoding="utf-8") as f:
        f.write(symbol_lib())
    with open(os.path.join(lib, "CO2.pretty", "WEMOS_D1_mini.kicad_mod"), "w", encoding="utf-8") as f:
        f.write(footprint())
    with open(os.path.join(ROOT, "sym-lib-table"), "w") as f:
        f.write('(sym_lib_table\n  (version 7)\n  (lib (name "CO2")(type "KiCad")(uri "${KIPRJMOD}/lib/CO2.kicad_sym")(options "")(descr "Projektbibliothek CO2-Ampel"))\n)\n')
    with open(os.path.join(ROOT, "fp-lib-table"), "w") as f:
        f.write('(fp_lib_table\n  (version 7)\n  (lib (name "CO2")(type "KiCad")(uri "${KIPRJMOD}/lib/CO2.pretty")(options "")(descr "Projektbibliothek CO2-Ampel"))\n)\n')
    print("Bibliothek erzeugt")
