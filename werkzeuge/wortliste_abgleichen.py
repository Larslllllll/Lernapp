"""Die Sperrliste gegen öffentliche Wortlisten abgleichen.

    .venv/Scripts/python.exe werkzeuge/wortliste_abgleichen.py

Lädt bekannte Listen von GitHub und meldet, welche ihrer Einträge unser
Filter noch nicht fängt. **Übernommen wird nichts automatisch** - das ist
Absicht.

Der Grund: die öffentlichen Listen sind Schimpfwortlisten, unsere ist eine
Liste schwerer Beleidigungen. Wer `arsch`, `kacke` und `bumsen` blind
übernimmt, sperrt Vokabeln, die in einem Sprachkurs vorkommen dürfen - und
fängt `nigg3r` trotzdem nicht, weil dort nur Grundformen ohne Normalisierung
stehen.

Das Skript ist deshalb ein Vorschlagswerkzeug: Ausgabe ansehen, einzeln
entscheiden, die gewünschten Zeilen von Hand in `GESPERRT` eintragen.
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from lernapp.core import wortfilter  # noqa: E402

LDNOOBW = ("https://raw.githubusercontent.com/LDNOOBW/"
           "List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words/master/")

QUELLEN = {
    "LDNOOBW deutsch": LDNOOBW + "de",
    "LDNOOBW englisch": LDNOOBW + "en",
    "LDNOOBW französisch": LDNOOBW + "fr",
}


def hole(url: str) -> list[str]:
    anfrage = urllib.request.Request(url, headers={"User-Agent": "LernApp"})
    try:
        with urllib.request.urlopen(anfrage, timeout=30) as antwort:
            roh = antwort.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as grund:
        print(f"  nicht erreichbar: {grund}", file=sys.stderr)
        return []
    return [zeile.strip() for zeile in roh.splitlines() if zeile.strip()]


def main() -> int:
    print(f"Unsere Sperrliste: {len(wortfilter.GESPERRT)} Grundformen\n")

    for name, url in QUELLEN.items():
        woerter = hole(url)
        if not woerter:
            continue
        offen = [wort for wort in woerter if wortfilter.ist_sauber(wort)]
        gefangen = len(woerter) - len(offen)
        print(f"{name}: {len(woerter)} Einträge, {gefangen} davon fangen wir schon")
        if offen:
            print(f"  noch nicht abgedeckt ({len(offen)}):")
            for zeile in range(0, len(offen), 6):
                print("    " + ", ".join(offen[zeile:zeile + 6]))
        print()

    print("Nichts davon wurde übernommen. Was du sperren willst, trägst du in")
    print("GESPERRT in lernapp/core/wortfilter.py ein - eine Zeile je Wort.")
    print("Danach `pytest tests/test_wortfilter.py` laufen lassen: dort prüft")
    print("ein Test alle 1516 echten Karten auf Fehlalarme.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
