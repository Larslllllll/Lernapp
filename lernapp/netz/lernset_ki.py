"""Aus rohem Text ein Lernset machen - mit einem Sprachmodell.

Das ist die Stelle, an der ein Modell wirklich etwas kann, das sich nicht
ausrechnen lässt: aus einer abgetippten Buchseite erkennen, was Vokabel ist,
was Übersetzung, und was Überschrift, Seitenzahl oder Übungsanweisung.

**Ausgegeben wird bewusst nur Text im Format `frage;antwort`** - genau das,
was der vorhandene Textimport ohnehin versteht. Das Ergebnis läuft danach
durch dieselbe Vorschau wie ein von Hand eingefügter Text: der Nutzer sieht
jede Zeile, bevor irgendetwas gespeichert wird. Ein Modell, das sich irrt,
kann damit nichts kaputt machen.

Kennt weder Qt noch Dateien. Der Zugang wird hereingereicht.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .ki import KIFehler, Zugang, frage

# Mehr Vokabeln als das kommen aus einer Buchseite nicht, und das Modell
# fängt jenseits davon an zu erfinden.
MAX_ZEILEN = 120

SYSTEM = (
    "Du hilfst beim Vokabellernen in der Schule. Du bekommst den rohen Text "
    "einer Buch- oder Arbeitsblattseite und ziehst daraus die Vokabelpaare. "
    "Du erfindest nichts dazu: was nicht im Text steht, kommt nicht vor."
)

AUFTRAG = """Ziehe aus dem folgenden Text alle Vokabelpaare heraus.

Regeln:
- Eine Zeile je Vokabel, im Format  fremdsprache;deutsch
- Bei unregelmässigen Verben mit drei Formen:  form1;form2;form3
- Überschriften, Seitenzahlen, Aufgabenstellungen, Grammatikerklärungen und
  Beispielsätze weglassen
- Artikel mitnehmen, wenn sie im Text stehen (la maison;das Haus)
- Nichts erfinden, nichts übersetzen, was nicht schon dasteht
- Keine Nummerierung, keine Aufzählungszeichen, keine Anführungszeichen
- Wenn du keine Vokabelpaare findest, gib genau NICHTS aus

Text:
---
{text}
---"""

# Was offensichtlich keine Vokabel ist. Das Modell hält sich nicht immer an
# die Regeln, und diese Zeilen fallen sonst als Karten im Lernset auf.
_MUELL = re.compile(
    r"^\s*(?:```|---|#|\*|\d+\s*[.)]\s*$|seite\b|page\b|unit\b|lektion\b|"
    r"vokabeln?\b|wortschatz\b|hier sind|folgende)", re.I)


@dataclass
class Vorschlag:
    """Was das Modell erkannt hat, plus was dabei aussortiert wurde."""

    zeilen: list[str] = field(default_factory=list)
    verworfen: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Genau das Format, das der vorhandene Textimport versteht."""
        return "\n".join(self.zeilen)

    def zusammenfassung(self) -> str:
        if not self.zeilen:
            return "Keine Vokabeln erkannt"
        satz = f"{len(self.zeilen)} Vokabeln erkannt"
        if self.verworfen:
            satz += f", {len(self.verworfen)} Zeilen verworfen"
        return satz


def _saeubere(roh: str) -> Vorschlag:
    """Antwort des Modells auf brauchbare Zeilen eindampfen.

    Das Modell liefert trotz klarer Ansage regelmässig Einleitungssätze,
    Codeblöcke und Nummerierungen mit. Die hier zu entfernen ist billiger,
    als sie den Nutzer in der Vorschau aussortieren zu lassen.
    """
    vorschlag = Vorschlag()
    for zeile in roh.splitlines():
        zeile = zeile.strip().strip("`")
        if not zeile:
            continue
        if _MUELL.match(zeile):
            vorschlag.verworfen.append(zeile)
            continue
        # Nummerierung am Anfang abschneiden: "1. la maison;das Haus"
        zeile = re.sub(r"^\s*\d+\s*[.)]\s*", "", zeile)
        felder = [t.strip() for t in zeile.split(";")]
        felder = [f for f in felder if f]
        if len(felder) not in (2, 3):
            vorschlag.verworfen.append(zeile)
            continue
        if any(len(f) > 80 for f in felder):
            # Ein ganzer Satz ist keine Vokabel.
            vorschlag.verworfen.append(zeile)
            continue
        vorschlag.zeilen.append(";".join(felder))
        if len(vorschlag.zeilen) >= MAX_ZEILEN:
            break
    return vorschlag


def erkenne_vokabeln(zugang: Zugang, text: str) -> Vorschlag:
    """Rohtext -> Vorschlag im Format `frage;antwort`.

    Wirft KIFehler mit einem Text, den man zeigen kann.
    """
    text = (text or "").strip()
    if not text:
        raise KIFehler("Der Text ist leer.")

    antwort = frage(zugang, SYSTEM, AUFTRAG.format(text=text), temperatur=0.1)
    vorschlag = _saeubere(antwort)
    if not vorschlag.zeilen:
        raise KIFehler(
            "In diesem Text konnte ich keine Vokabelpaare erkennen. "
            "Vielleicht ist es eine Textseite ohne Vokabelliste."
        )
    return vorschlag
