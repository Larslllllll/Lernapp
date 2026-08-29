"""Kartenmodell und Parsing des Legacy-Formats.

Auf der Platte liegt weiterhin das bestehende Format {"q": ..., "a": ...}.
Intern arbeiten wir mit echten Objekten. Das Parsen ist verlustfrei:
`card.legacy_item()` erzeugt exakt das Dict zurueck, aus dem die Karte kam.

Wichtig: `legacy_q` bleibt der Identitaetsschluessel fuer den Fortschritt,
weil progress.json historisch nach der Frage-Zeichenkette indiziert ist.
"""
from __future__ import annotations

from dataclasses import dataclass

BLANK = "___"
TRIPLE_TRENNER = ", "


def _antwort_varianten(antwort: str) -> list[str]:
    """Akzeptierte Alternativen einer normalen Antwort ("a, b" oder "a; b")."""
    roh = antwort.replace(";", ",").split(",")
    return [t.strip().lower() for t in roh if t.strip()]


@dataclass(frozen=True)
class NormalCard:
    question: str
    answer: str

    @property
    def key(self) -> str:
        return self.question

    @property
    def is_triple(self) -> bool:
        return False

    def erwartet(self, rueckwaerts: bool = False) -> str:
        """Der zu tippende Text. Rueckwaerts wird die Frage abgefragt."""
        return self.question if rueckwaerts else self.answer

    def zeigt(self, rueckwaerts: bool = False) -> str:
        return self.answer if rueckwaerts else self.question

    def akzeptierte_antworten(self, rueckwaerts: bool = False) -> list[str]:
        """Alle gueltigen Eingaben. "das Rad, das Fahrrad" ergibt zwei."""
        return _antwort_varianten(self.erwartet(rueckwaerts))

    def pruefe(self, eingabe: str, rueckwaerts: bool = False) -> bool:
        return eingabe.strip().lower() in self.akzeptierte_antworten(rueckwaerts)

    def weitere_loesungen(self, eingabe: str, rueckwaerts: bool = False) -> list[str]:
        getippt = eingabe.strip().lower()
        return [v for v in _antwort_varianten(self.erwartet(rueckwaerts)) if v != getippt]

    def legacy_item(self) -> dict:
        return {"q": self.question, "a": self.answer}


@dataclass(frozen=True)
class TripleCard:
    """Eine Karte eines Drei-Formen-Pakets (z.B. go / went / gone).

    `forms`    - alle drei Formen in ihrer festen Reihenfolge
    `revealed` - Index der Form, die auf der Karte sichtbar ist (0, 1 oder 2)
    """
    forms: tuple[str, str, str]
    revealed: int

    def __post_init__(self) -> None:
        if len(self.forms) != 3:
            raise ValueError(f"Triple braucht genau 3 Formen, hat {len(self.forms)}")
        if self.revealed not in (0, 1, 2):
            raise ValueError(f"revealed muss 0..2 sein, ist {self.revealed}")

    @property
    def is_triple(self) -> bool:
        return True

    @property
    def package_key(self) -> tuple[str, str, str]:
        """Identitaet des Pakets. Geordnetes Tupel - im Gegensatz zum frueheren
        frozenset kollabieren doppelte Formen (must/had to/had to) hier nicht."""
        return self.forms

    @property
    def hidden_indices(self) -> tuple[int, int]:
        return tuple(i for i in range(3) if i != self.revealed)  # type: ignore[return-value]

    @property
    def erwartet(self) -> tuple[str, str]:
        """Die beiden gesuchten Formen, in Spaltenreihenfolge."""
        i, j = self.hidden_indices
        return self.forms[i], self.forms[j]

    @property
    def sichtbar(self) -> str:
        return self.forms[self.revealed]

    @property
    def key(self) -> str:
        """Legacy-Fragezeichenkette - Schluessel fuer Streaks/Fortschritt."""
        teile = [BLANK, BLANK, BLANK]
        teile[self.revealed] = self.forms[self.revealed]
        return " ".join(teile)

    def slots(self) -> list[tuple[int, str | None]]:
        """Anzeige-Bauplan: je Spalte (index, Text) - Text None heisst Eingabefeld."""
        return [(i, self.forms[i] if i == self.revealed else None) for i in range(3)]

    def pruefe(self, eingaben: list[str]) -> bool:
        if len(eingaben) != 2:
            return False
        getippt = [e.strip().lower() for e in eingaben]
        return getippt == [f.strip().lower() for f in self.erwartet]

    def volle_loesung(self) -> str:
        return " . ".join(self.forms)

    def legacy_item(self) -> dict:
        return {"q": self.key, "a": TRIPLE_TRENNER.join(self.erwartet)}


def parse_card(item: dict) -> NormalCard | TripleCard:
    """Legacy-Item -> Karte. Faellt auf NormalCard zurueck, wenn kein Triple."""
    q, a = item["q"], item["a"]
    triple = _parse_triple(q, a)
    return triple if triple is not None else NormalCard(question=q, answer=a)


def _parse_triple(q: str, a: str) -> TripleCard | None:
    """Erkennt eine Triple-Karte.

    Getrennt wird an BLANK, nicht an Whitespace. Genau daran ist die alte
    Implementierung bei mehrwortigen Formen ("been able", "had to") zerbrochen.
    """
    if BLANK not in q:
        return None
    segmente = q.split(BLANK)
    if len(segmente) != 3:          # genau zwei Luecken erwartet
        return None
    gefuellt = [(i, s.strip()) for i, s in enumerate(segmente) if s.strip()]
    if len(gefuellt) != 1:          # genau eine sichtbare Form erwartet
        return None
    revealed, sichtbar = gefuellt[0]

    versteckt = [t.strip() for t in a.split(TRIPLE_TRENNER)]
    if len(versteckt) != 2 or not all(versteckt):
        return None

    forms: list[str] = [""] * 3
    forms[revealed] = sichtbar
    for pos, wert in zip((i for i in range(3) if i != revealed), versteckt):
        forms[pos] = wert
    return TripleCard(forms=(forms[0], forms[1], forms[2]), revealed=revealed)


def parse_items(items: list[dict]) -> list[NormalCard | TripleCard]:
    return [parse_card(it) for it in items]


def gruppiere_pakete(karten: list) -> dict[tuple[str, str, str], list[TripleCard]]:
    """Triple-Karten nach Paket buendeln."""
    pakete: dict[tuple[str, str, str], list[TripleCard]] = {}
    for k in karten:
        if k.is_triple:
            pakete.setdefault(k.package_key, []).append(k)
    return pakete


def lerneinheiten(karten: list) -> int:
    """Zaehlbare Lerneinheiten: ein Triple-Paket zaehlt als EINS.

    Genau diese Zahl muss ueberall gleich sein - Sidebar, Fortschrittsbalken
    und Statistik. Die alte Version hat hier je nach Ansicht unterschiedlich
    gezaehlt.
    """
    normale = sum(1 for k in karten if not k.is_triple)
    return normale + len(gruppiere_pakete(karten))
