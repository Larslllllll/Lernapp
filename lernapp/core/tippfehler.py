"""Erkennen, ob eine Antwort nur knapp danebenliegt.

`maisson` statt `maison` ist kein Wissenslücke, sondern ein verrutschter
Finger. Wer dafür dieselbe Strafe bekommt wie für eine völlig falsche
Antwort, hört auf zu tippen und fängt an zu raten.

Reine Rechnerei, keine GUI, kein I/O, kein Modell. Absichtlich **ohne**
Bibliothek: der Damerau-Levenshtein-Abstand sind zwanzig Zeilen, und eine
Abhängigkeit müsste ins Bundle.

**Entscheidend ist nicht die Länge allein, sondern die ART des Fehlers.**
Das war der erste Entwurf und er fiel durch: bei „ab vier Zeichen ist ein
Fehler erlaubt" gingen `Maus` für `Haus`, `mein` für `sein` und `gehen` für
`sehen` durch. Ein Vokabeltrainer, der das durchwinkt, bringt falsche
Vokabeln bei.

Der Unterschied: ein **ersetzter** Buchstabe ergibt in kurzen Wörtern fast
immer ein anderes echtes Wort - genau so sind Minimalpaare gebaut. Ein
**eingefügter, fehlender oder vertauschter** Buchstabe dagegen ergibt fast nie
eines: `hasu`, `hauss`, `hus` sind keine Wörter, sondern verrutschte Finger.

Deshalb drei Regeln:

- eingefügt, fehlend, vertauscht -> ab vier Zeichen verziehen
- ersetzt -> erst ab acht Zeichen verziehen
- zwei Fehler -> erst ab zwölf Zeichen

**Und eine vierte Regel, die aus den echten Daten kam.** Ein Lauf über 76 229
Antwortpaare aus Lars' Lernsets fand 68 Fälle, in denen zwei richtige
Antworten füreinander als Vertipper durchgingen:

    bit <-> bite     broke <-> broken     choose <-> chose
    bled <-> bleed   blow  <-> blown      bought <-> brought

Das sind keine Vertipper, sondern genau die Formen, die gelernt werden
sollen. Deshalb: **was selbst eine gültige Antwort in diesem Lernset ist,
gilt nie als Vertipper.** Wer `broken` tippt, hat sich nicht vertippt - er hat
die falsche Form genommen, und genau das soll er merken.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass

# Ab dieser Länge (des erwarteten Wortes) wie viele Abweichungen noch als
# Tippfehler durchgehen. Absteigend gelesen.
_TOLERANZ: tuple[tuple[int, int], ...] = ((12, 2), (4, 1))

# Ab dieser Länge wird auch ein ERSETZTER Buchstabe verziehen. Darunter ist
# er zu oft ein anderes Wort: Haus/Maus, sein/mein, gehen/sehen.
MINDESTLAENGE_FUER_ERSETZUNG = 8


@dataclass(frozen=True)
class Vergleich:
    """Was an einer Antwort dran war."""

    richtig: bool
    fast: bool
    abstand: int
    nur_akzente: bool
    erwartet: str

    @property
    def grund(self) -> str:
        """Ein kurzer Satz für die Oberfläche. Leer, wenn es nichts zu sagen gibt."""
        if self.richtig:
            return ""
        if not self.fast:
            return ""
        if self.nur_akzente:
            return "Fast — es fehlen nur die Akzente."
        if self.abstand == 1:
            return "Fast — ein Buchstabe stimmt nicht."
        return "Fast — zwei Buchstaben stimmen nicht."


def ohne_akzente(text: str) -> str:
    """`élève` -> `eleve`. Umlaute bleiben unterscheidbar (ä -> a)."""
    zerlegt = unicodedata.normalize("NFKD", text)
    return "".join(z for z in zerlegt if not unicodedata.combining(z))


def abstand(a: str, b: str) -> int:
    """Damerau-Levenshtein: Einfügen, Löschen, Ersetzen, **Vertauschen**.

    Das Vertauschen ist der Grund, warum es nicht der einfache
    Levenshtein-Abstand ist: `maisno` statt `maison` ist ein Anschlag zu
    früh, kein zweiter Fehler.
    """
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    vorherige: list[int] = []
    zeile = list(range(len(b) + 1))
    for i, za in enumerate(a, start=1):
        vorvorherige, vorherige, zeile = vorherige, zeile, [i] + [0] * len(b)
        for j, zb in enumerate(b, start=1):
            zeile[j] = min(
                vorherige[j] + 1,            # löschen
                zeile[j - 1] + 1,            # einfügen
                vorherige[j - 1] + (za != zb),  # ersetzen
            )
            if (i > 1 and j > 1 and za == b[j - 2] and a[i - 2] == zb):
                zeile[j] = min(zeile[j], vorvorherige[j - 2] + 1)  # vertauschen
    return zeile[-1]


def erlaubte_abweichung(erwartet: str) -> int:
    """Wie viele Fehler bei diesem Wort noch als Tippfehler gelten."""
    laenge = len(erwartet)
    for ab, wie_viele in _TOLERANZ:
        if laenge >= ab:
            return wie_viele
    return 0


def _ist_reine_ersetzung(a: str, b: str) -> bool:
    """Gleich lang und keine Vertauschung - also wurden nur Zeichen ersetzt.

    Eine Vertauschung (`hasu` statt `haus`) sieht auf den ersten Blick aus
    wie zwei Ersetzungen, ist aber ein einzelner verrutschter Anschlag.
    """
    if len(a) != len(b):
        return False
    unterschiede = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    if len(unterschiede) == 2:
        i, j = unterschiede
        if j == i + 1 and a[i] == b[j] and a[j] == b[i]:
            return False
    return True


def ist_tippfehler(getippt: str, erwartet: str) -> bool:
    """Liegt die Eingabe nur knapp daneben - oder ist es ein anderes Wort?"""
    entfernung = abstand(getippt, erwartet)
    if entfernung == 0:
        return False
    erlaubt = erlaubte_abweichung(erwartet)
    if entfernung > erlaubt:
        return False
    if entfernung == 1 and _ist_reine_ersetzung(getippt, erwartet):
        return len(erwartet) >= MINDESTLAENGE_FUER_ERSETZUNG
    return True


def vergleiche(eingabe: str, erwartete: list[str],
               andere_antworten: object = ()) -> Vergleich:
    """Eingabe gegen alle gültigen Antworten prüfen.

    Zurück kommt der beste Treffer: erst auf genau richtig, dann auf knapp
    daneben. `erwartete` sind die Alternativen dieser Karte - "das Rad, das
    Fahrrad" ergibt zwei.

    `andere_antworten` sind die gültigen Antworten der ÜBRIGEN Karten des
    Lernsets. Was dort vorkommt, ist kein Vertipper, sondern die falsche
    Vokabel - siehe die vierte Regel oben.
    """
    getippt = " ".join(eingabe.strip().lower().split())
    kandidaten = [" ".join(e.strip().lower().split()) for e in erwartete if e.strip()]

    if not getippt or not kandidaten:
        return Vergleich(False, False, 99, False, kandidaten[0] if kandidaten else "")

    if getippt in kandidaten:
        return Vergleich(True, False, 0, False, getippt)

    bester = min(kandidaten, key=lambda k: abstand(getippt, k))
    entfernung = abstand(getippt, bester)

    # Ist das Getippte selbst eine richtige Antwort aus diesem Lernset? Dann
    # war es keine verrutschte Hand, sondern die falsche Vokabel. Diese
    # Prüfung kommt VOR der Akzentprüfung: `ou` und `où` sind zwei Wörter.
    fremde = {" ".join(str(a).strip().lower().split()) for a in andere_antworten}
    if getippt in fremde:
        return Vergleich(False, False, entfernung, False, bester)

    # Nur die Akzente vergessen? Das ist die häufigste Abweichung in
    # Französisch und soll auch so benannt werden.
    nur_akzente = any(ohne_akzente(getippt) == ohne_akzente(k) for k in kandidaten)
    if nur_akzente:
        return Vergleich(False, True, entfernung, True, bester)

    return Vergleich(False, ist_tippfehler(getippt, bester), entfernung, False, bester)
