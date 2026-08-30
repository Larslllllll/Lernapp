"""Aus dem Logo-PNG die ico.ico bauen.

    .venv/Scripts/python.exe packaging/icon_bauen.py

Windows wählt je nach Ort eine andere Größe aus der Datei: 16 px in der
Titelleiste, 32 px in der Taskleiste, 48 px im Explorer, 256 px in der
Kachelansicht. Eine .ico mit nur einer Größe lässt Windows selbst
herunterrechnen, und das sieht bei 16 px sichtbar matschig aus.

Die Quelle hat rundherum Leerraum um die abgerundete Kachel. Der wird
abgeschnitten, sonst schrumpft das eigentliche Zeichen in der Taskleiste auf
zwei Drittel der verfügbaren Fläche.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover - reine Werkzeugbedingung
    print("FEHLER: Pillow fehlt.  .venv/Scripts/python.exe -m pip install pillow",
          file=sys.stderr)
    raise SystemExit(1)

WURZEL = Path(__file__).resolve().parent.parent
QUELLE = WURZEL / "packaging" / "icon-quelle.png"
ZIEL = WURZEL / "ico.ico"

# Was Windows tatsächlich abfragt. 256 kommt als PNG in die Datei, der Rest
# als BMP - das ist die Aufteilung, die auch Inno Setup ohne Murren frisst.
GROESSEN = [16, 24, 32, 48, 64, 128, 256]

# Wie stark ein Pixel sich vom Rand unterscheiden muss, um als Teil der
# Kachel zu gelten. Die Kachel ist nur wenig heller als der Hintergrund,
# deshalb ein kleiner Wert.
SCHWELLE = 6


def kachel_finden(bild: Image.Image) -> tuple[int, int, int, int]:
    """Den Rand um die Kachel abschneiden.

    Als Hintergrundfarbe gilt die Ecke oben links - die liegt garantiert
    ausserhalb des Zeichens.
    """
    rgb = bild.convert("RGB")
    hintergrund = rgb.getpixel((0, 0))

    def abweichend(pixel: tuple[int, int, int]) -> bool:
        return max(abs(a - b) for a, b in zip(pixel, hintergrund)) > SCHWELLE

    breite, hoehe = rgb.size
    daten = rgb.load()
    links, oben, rechts, unten = breite, hoehe, 0, 0
    for y in range(hoehe):
        for x in range(breite):
            if abweichend(daten[x, y]):
                links = min(links, x)
                rechts = max(rechts, x)
                oben = min(oben, y)
                unten = max(unten, y)
    if rechts <= links or unten <= oben:
        raise SystemExit("FEHLER: keine Kachel gefunden - ist das Bild einfarbig?")
    return links, oben, rechts + 1, unten + 1


def quadratisch(kasten: tuple[int, int, int, int],
                groesse: tuple[int, int]) -> tuple[int, int, int, int]:
    """Den Ausschnitt auf ein Quadrat erweitern, mittig, innerhalb des Bildes.

    Ein nicht quadratischer Ausschnitt würde beim Skalieren verzerren.
    """
    links, oben, rechts, unten = kasten
    breite, hoehe = rechts - links, unten - oben
    kante = max(breite, hoehe)
    mitte_x, mitte_y = links + breite / 2, oben + hoehe / 2
    links = int(round(mitte_x - kante / 2))
    oben = int(round(mitte_y - kante / 2))
    links = max(0, min(links, groesse[0] - kante))
    oben = max(0, min(oben, groesse[1] - kante))
    return links, oben, links + kante, oben + kante


def main() -> int:
    if not QUELLE.exists():
        print(f"FEHLER: {QUELLE} fehlt.", file=sys.stderr)
        return 1

    bild = Image.open(QUELLE).convert("RGBA")
    kasten = quadratisch(kachel_finden(bild), bild.size)
    ausschnitt = bild.crop(kasten)

    # LANCZOS statt der Voreinstellung: bei 16 px entscheidet die Qualität
    # des Herunterrechnens darüber, ob das Zeichen noch erkennbar ist.
    groesste = ausschnitt.resize((256, 256), Image.LANCZOS)
    groesste.save(ZIEL, format="ICO", sizes=[(g, g) for g in GROESSEN])

    print(f"Quelle       {QUELLE.name}  {bild.width}x{bild.height}")
    print(f"Ausschnitt   {kasten}  ({ausschnitt.width}x{ausschnitt.height})")
    print(f"Groessen     {', '.join(str(g) for g in GROESSEN)}")
    print(f"Ausgabe      {ZIEL}  ({ZIEL.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
