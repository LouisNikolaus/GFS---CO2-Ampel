# CO2-Ampel mit D1 mini (ESP8266)

Trägerplatine 100 × 60 mm (2 Lagen, nur THT-Bauteile) + 3D-gedrucktes Gehäuse 105 × 65 × 27 mm.

## Ordner

```
Platine/        KiCad-10-Projekt (CO2-Ampel.kicad_pro hier öffnen)
  lib/          Projektbibliothek: Symbol + Footprint D1 mini
  fertigung/    Gerber-ZIP, Stückliste, Layout-PDF, Renderings
  pruefberichte/  ERC/DRC-Berichte
  scripts/      Generatoren für Schaltplan, Platine und Router
gehaeuse/       STL-Dateien für den 3D-Druck
  scripts/      Gehäuse-Generator (parametrisch)
ESP-Code/       Firmware für den D1 mini (folgt)
```

| Datei | Inhalt |
|---|---|
| `Platine/CO2-Ampel_Schaltplan.pdf` | Schaltplan zum Ansehen ohne KiCad |
| `Platine/fertigung/CO2-Ampel_Gerber.zip` | Gerber + Bohrdaten für JLCPCB / Aisler / PCBWay |
| `Platine/fertigung/Stueckliste.csv` | Stückliste |
| `gehaeuse/Unterschale.stl`, `gehaeuse/Deckel.stl` | Druckdateien (Deckel liegt schon richtig herum) |

## Belegung D1 mini

| Pin | Funktion |
|---|---|
| D1 (GPIO5) | I2C SCL (Display + Sensor) |
| D2 (GPIO4) | I2C SDA |
| D3 (GPIO0) | Taster gegen GND (interner Pull-up) |
| D5 / D6 / D7 | LED rot / gelb / grün |
| D8 (GPIO15) | Summer über BC547 |
| 5V / 3V3 / G | Versorgung (über USB des D1 mini) |

## Zusätzlich zur Stückliste

- 2 × Buchsenleiste 1×8, RM 2,54 (für den D1 mini)
- 4 × Schraube M3 × 8 (Platine auf Abstandshalter, selbstschneidend)
- Aktiver Summer 5 V, 12 mm, Rastermaß 7,6 mm
- Taster 6 × 6 mm mit **13 mm Bauhöhe**

## Vor der Bestellung prüfen

1. **Pinfolge des CO2-Sensors**: J2 ist VCC–GND–SCL–SDA belegt. Das Sensormodul (SCD40/SCD41/SCD30 …) vergleichen.
2. **Pinfolge des OLED**: J1 ist GND–VCC–SCL–SDA belegt. Manche Displays haben VCC–GND!
3. **JP1** (Lötbrücke): ab Werk 3,3 V für den Sensor. Für 5 V die Brücke 1-2 auftrennen und 2-3 verbinden.
4. **R1/R2** nur bestücken, wenn weder Display noch Sensor eigene Pull-ups haben.

## Gehäuse

- Material: PETG oder PLA, 0,2 mm Schichthöhe, keine Stützstrukturen nötig.
- Unterschale mit der Öffnung nach oben drucken, den Deckel mit der Sichtseite aufs Druckbett.
- Der Deckel wird nur gesteckt (Klemmrand). Wenn er zu stramm sitzt, in `gehaeuse/scripts/gen_case.py` den Wert `LIP_CLEAR` erhöhen.
- Die **Trennwand** im Deckel sitzt über dem Schlitz in der Platine. Sie trennt den Sensor thermisch vom warmen ESP8266 und verbessert so die Temperaturmessung.
- **LEDs** erst einlöten, wenn der Deckel aufgesetzt ist. So stecken sie genau in den Löchern.
- **Wichtig:** Die Bauhöhe hängt davon ab, wie D1 mini und Display gesteckt sind. Maßgeblich ist der Parameter `PARTS_H` (Standard 16 mm über Platinenoberseite). Nachmessen und bei Bedarf anpassen:
  `python gehaeuse/scripts/gen_case.py`

## Neu erzeugen

Alle Befehle im Hauptordner ausführen (normales Python braucht `pip install manifold3d numpy`):

```
python Platine/scripts/gen_lib.py
python Platine/scripts/gen_sch.py
kicad-cli sch export netlist --format kicadsexpr -o Platine/CO2-Ampel.net Platine/CO2-Ampel.kicad_sch
"C:\Program Files\KiCad\10.0\bin\python.exe" Platine/scripts/gen_pcb.py
"C:\Program Files\KiCad\10.0\bin\python.exe" Platine/scripts/route_pcb.py
python gehaeuse/scripts/gen_case.py
```

Achtung: `gen_pcb.py` und `route_pcb.py` überschreiben die Platine. Wer das Layout von Hand in KiCad weiterbearbeitet, führt die Skripte danach nicht mehr aus.
