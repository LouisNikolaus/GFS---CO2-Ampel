# ESP-Code

Hier kommt die Firmware für den D1 mini (ESP8266) hin, z. B. als Arduino-Sketch `CO2-Ampel/CO2-Ampel.ino`.

## Pinbelegung (aus dem Schaltplan)

| D1-mini-Pin | GPIO | Funktion |
|---|---|---|
| D1 | GPIO5 | I2C SCL (OLED + CO2-Sensor) |
| D2 | GPIO4 | I2C SDA |
| D3 | GPIO0 | Taster gegen GND → `INPUT_PULLUP`, beim Einschalten nicht drücken |
| D5 | GPIO14 | LED rot |
| D6 | GPIO12 | LED gelb |
| D7 | GPIO13 | LED grün |
| D8 | GPIO15 | Summer über BC547 (HIGH = an) |
| D4 | GPIO2 | frei (blaue Onboard-LED) |
| D0, A0, TX, RX | – | frei |

OLED: SSD1306 128×64, I2C-Adresse meist 0x3C.

## Geplante Funktionen

- CO2, Temperatur und Luftfeuchte messen und auf dem OLED anzeigen
- Ampel: grün < 1000 ppm, gelb < 1500 ppm, rot ≥ 1500 ppm, Summer bei Rot
- WLAN: Messwerte bereitstellen (Webseite oder MQTT)
