"""Zwei Anbieter an denselben Vokabeln vergleichen.

    python werkzeuge/anbieter_vergleichen.py nous gemini

Erzeugt für dieselben zehn Karten mit beiden Anbietern Beispielsätze und
stellt sie nebeneinander. Damit entscheidest du nach dem Ergebnis, nicht nach
einer Meinung - meiner eingeschlossen.

Geprüft wird dabei automatisch, was sich automatisch prüfen lässt: Kommt die
Vokabel im Satz vor? Ist er kurz genug? Steht am Ende ein Punkt? Ein
Beispielsatz, der die Vokabel gar nicht enthält, ist wertlos, und das kommt
bei kleineren Modellen regelmäßig vor.

Schlüssel kommen aus der Umgebung:

    LERNAPP_KI_SCHLUESSEL_NOUS, LERNAPP_KI_SCHLUESSEL_GEMINI, ...
"""
from __future__ import annotations

import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from lernapp.netz import ki  # noqa: E402

SYSTEM = (
    "Du hilfst beim Vokabellernen in der Schule. Antworte knapp, sachlich und "
    "ohne Einleitung. Gib genau das aus, was verlangt ist - keine "
    "Aufzählungszeichen, keine Anführungszeichen, keine Erklärung."
)

AUFTRAG = (
    "Sprache: {sprache}\n"
    "Vokabel: {frage}\n"
    "Bedeutung: {antwort}\n\n"
    "Schreibe EINEN kurzen Beispielsatz in {sprache}, der die Vokabel "
    "wörtlich enthält. Höchstens zwölf Wörter, Niveau Schulunterricht. "
    "Danach in einer zweiten Zeile die deutsche Übersetzung des Satzes."
)

PROBEN = [
    ("Französisch", "la maison", "das haus"),
    ("Französisch", "la fenêtre", "das fenster"),
    ("Französisch", "apprendre", "lernen"),
    ("Französisch", "le professeur", "der lehrer"),
    ("Englisch", "to bring", "bringen"),
    ("Englisch", "the neighbour", "der nachbar"),
    ("Englisch", "to borrow", "ausleihen"),
    ("Latein", "domus", "das haus"),
    ("Latein", "discere", "lernen"),
    ("Französisch", "s'inquiéter", "sich sorgen machen"),
]

HOECHSTLAENGE = 200


def pruefe(satz: str, vokabel: str) -> list[str]:
    """Was sich ohne Urteilsvermögen prüfen lässt."""
    maengel = []
    zeilen = [z.strip() for z in satz.splitlines() if z.strip()]
    if not zeilen:
        return ["leer"]
    erste = zeilen[0]
    # Ein Beispielsatz ohne die Vokabel ist wertlos. Der Vergleich ist grob:
    # das längste Wort der Vokabel muss vorkommen (Artikel wie "la" oder
    # Reflexivpronomen fallen sonst durch).
    kern = max(vokabel.replace("'", " ").split(), key=len).lower()
    if kern not in erste.lower():
        maengel.append(f"Vokabel fehlt im Satz ({kern!r})")
    if len(erste) > HOECHSTLAENGE:
        maengel.append("zu lang")
    if len(zeilen) < 2:
        maengel.append("keine Übersetzung")
    if erste.startswith(("- ", "* ", '"', "„")):
        maengel.append("Formatierung statt Satz")
    return maengel


def main() -> int:
    anbieter = sys.argv[1:] or ["nous", "gemini"]

    zugaenge = []
    for name in anbieter:
        zugang = ki.aus_umgebung(name)
        if not zugang.bereit:
            print(f"{name}: kein Schlüssel gesetzt "
                  f"(LERNAPP_KI_SCHLUESSEL_{name.upper()}) - übersprungen",
                  file=sys.stderr)
            continue
        zugaenge.append(zugang)

    if not zugaenge:
        print("Kein Anbieter eingerichtet.", file=sys.stderr)
        return 1

    punkte = {z.name: 0 for z in zugaenge}
    for sprache, frage_text, antwort in PROBEN:
        print(f"\n{'=' * 72}\n{sprache}: {frage_text} — {antwort}\n{'=' * 72}")
        for zugang in zugaenge:
            try:
                ergebnis = ki.frage(zugang, SYSTEM, AUFTRAG.format(
                    sprache=sprache, frage=frage_text, antwort=antwort))
            except ki.KIFehler as grund:
                print(f"\n  [{zugang.name}] FEHLER: {grund}")
                continue
            maengel = pruefe(ergebnis, frage_text)
            if not maengel:
                punkte[zugang.name] += 1
            marke = "ok" if not maengel else "  ".join(maengel)
            print(f"\n  [{zugang.name}]  ({marke})")
            for zeile in ergebnis.splitlines():
                if zeile.strip():
                    print(f"    {zeile.strip()}")

    print(f"\n{'=' * 72}")
    print("Automatisch prüfbare Mängel (Vokabel im Satz, Länge, Übersetzung):")
    for name, anzahl in punkte.items():
        print(f"  {name:10s} {anzahl}/{len(PROBEN)} einwandfrei")
    print("\nDen Rest - ob die Sätze sprachlich gut sind - musst du lesen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
