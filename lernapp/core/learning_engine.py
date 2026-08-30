"""Lern-Engine: Kartenauswahl, Antwortprüfung, Runden.

Enthält bewusst KEINE GUI-Aufrufe. Statt Widgets zu verändern, liefert die
Engine Zustände und Ergebnisse zurück; die Oberfläche entscheidet, wie sie
das darstellt.

Der Zufall wird injiziert (`rng`), damit die Kartenauswahl reproduzierbar
testbar ist.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import rules, tippfehler
from .cards import NormalCard, TripleCard, gruppiere_pakete, lerneinheiten
from .progress import SetProgress

VORWAERTS = "→"    # Pfeil rechts
RUECKWAERTS = "←"  # Pfeil links
GEMISCHT = "⇄"     # Pfeile gemischt

_BIAS_MIN, _BIAS_MAX = 0.75, 0.85


@dataclass
class Frage:
    """Was dem Lernenden gerade gezeigt wird."""

    card: NormalCard | TripleCard
    rueckwaerts: bool = False

    @property
    def ist_triple(self) -> bool:
        return self.card.is_triple

    @property
    def anzeige(self) -> str:
        if self.card.is_triple:
            return self.card.sichtbar
        return self.card.zeigt(self.rueckwaerts)


class _OhneEigene:
    """Menge minus ein paar Einträge, ohne sie zu kopieren.

    Gebraucht wird nur `in`. Ein `set.difference` über 350 Wörter bei jeder
    falschen Antwort war messbar teuer.
    """

    __slots__ = ("_menge", "_eigene")

    def __init__(self, menge: set[str], eigene) -> None:
        self._menge = menge
        self._eigene = frozenset(eigene)

    def __contains__(self, wert: object) -> bool:
        return wert in self._menge and wert not in self._eigene


@dataclass
class Ergebnis:
    """Was eine Antwort bewirkt hat."""

    richtig: bool
    xp: int = 0
    level_up: bool = False
    combo: int = 0
    multiplikator: float = 1.0
    loesung: str = ""
    weitere: list[str] = field(default_factory=list)
    # "Fast" ist weder richtig noch falsch: die Karte kommt wieder, aber
    # Combo und Streak bleiben stehen. Siehe core.tippfehler.
    fast: bool = False
    hinweis: str = ""


class SessionZustand:
    LAEUFT = "laeuft"
    RUNDE_FERTIG = "runde_fertig"
    FERTIG = "fertig"


class LearningSession:
    """Eine Lernsitzung über die Karten eines Lernsets."""

    def __init__(
        self,
        karten: list,
        fortschritt: SetProgress | None = None,
        rng: random.Random | None = None,
        richtung: str = GEMISCHT,
    ) -> None:
        # Nach Schlüssel deduplizieren. Der Fortschritt ist historisch nach der
        # Frage-Zeichenkette indiziert; zwei Karten mit gleicher Frage wären
        # derselbe Eintrag und würden sonst doppelt gezählt.
        self._nach_key: dict[str, NormalCard | TripleCard] = {}
        for k in karten:
            self._nach_key.setdefault(k.key, k)
        self.karten = list(self._nach_key.values())
        # Je Richtung einmal gebildet, siehe _fremde_antworten.
        self._alle_antworten: dict[bool, set[str]] = {}

        self.fortschritt = fortschritt or SetProgress()
        self.rng = rng or random.Random()
        self.richtung = richtung
        self.runde = 1

        self._pakete = gruppiere_pakete(self.karten)
        self._paket_keys = {
            k.key: [c.key for c in self._pakete[k.package_key]]
            for k in self.karten
            if k.is_triple
        }
        self._bias = self.rng.uniform(_BIAS_MIN, _BIAS_MAX)

        for k in self.karten:
            self.fortschritt.streaks.setdefault(k.key, 0)

        self.aktuelle_frage: Frage | None = None

    # -- Zustand --------------------------------------------------------------

    @property
    def offene_keys(self) -> list[str]:
        return [k.key for k in self.karten if self.fortschritt.streaks.get(k.key, 0) < 1]

    @property
    def zustand(self) -> str:
        if self.offene_keys:
            return SessionZustand.LAEUFT
        if self._fehlerkarten():
            return SessionZustand.RUNDE_FERTIG
        return SessionZustand.FERTIG

    def fortschritt_zaehler(self) -> tuple[int, int]:
        """(gelernt, gesamt) in Lerneinheiten - ein Triple-Paket zählt als eins.

        Diese Zahl ist die einzige Wahrheit. Sidebar, Fortschrittsbalken und
        Statistik müssen alle sie verwenden.
        """
        streaks = self.fortschritt.streaks
        gesamt = lerneinheiten(self.karten)
        fertig = sum(
            1 for k in self.karten if not k.is_triple and streaks.get(k.key, 0) >= 1
        )
        for gruppe in self._pakete.values():
            if all(streaks.get(c.key, 0) >= 1 for c in gruppe):
                fertig += 1
        return fertig, gesamt

    def _streak_gruppe(self, card) -> list[str]:
        """Alle Streak-Schlüssel, die bei einem Fehler gemeinsam fallen."""
        return self._paket_keys.get(card.key, [card.key])

    def _fremde_antworten(self, card, rueckwaerts: bool) -> set[str]:
        """Alle gültigen Antworten der ÜBRIGEN Karten dieses Lernsets.

        Ohne diesen Kontext gilt `broken` als Vertipper von `broke` - und
        genau diesen Unterschied soll man ja lernen.

        Die Gesamtmenge wird je Richtung einmal gebildet und behalten. Sie
        bei jeder falschen Antwort neu über alle Karten aufzubauen hat den
        Testlauf von 14 auf 72 Sekunden gebracht - bei 351 Karten in einem
        Lernset ist das im Lernen genauso spürbar.
        """
        menge = self._alle_antworten.get(rueckwaerts)
        if menge is None:
            menge = set()
            for andere in self.karten:
                if not andere.is_triple:
                    menge.update(andere.akzeptierte_antworten(rueckwaerts))
            self._alle_antworten[rueckwaerts] = menge
        # Die eigenen Antworten der Karte gehören nicht dazu - sonst gälte
        # die richtige Antwort als "andere Vokabel". Nur diese wenigen
        # abziehen, nicht die ganze Menge kopieren.
        return _OhneEigene(menge, card.akzeptierte_antworten(rueckwaerts))

    def _fehlerkarten(self) -> set[str]:
        return {
            q
            for q, n in self.fortschritt.round_errors.items()
            if n > 0 and q in self.fortschritt.streaks
        }

    # -- Ablauf ---------------------------------------------------------------

    def naechste_frage(self) -> Frage | None:
        """Wählt die nächste Karte. None heisst: Runde vorbei."""
        offen = self.offene_keys
        if not offen:
            self.aktuelle_frage = None
            return None

        gewichte = [self.fortschritt.gewicht(q) for q in offen]
        key = self.rng.choices(offen, weights=gewichte, k=1)[0]
        card = self._nach_key[key]

        if card.is_triple:
            rueckwaerts = False
        elif self.richtung == GEMISCHT:
            rueckwaerts = self.rng.random() >= self._bias
        else:
            rueckwaerts = self.richtung == RUECKWAERTS

        self.aktuelle_frage = Frage(card=card, rueckwaerts=rueckwaerts)
        return self.aktuelle_frage

    def antworte(self, eingabe) -> Ergebnis:
        """Prüft die Antwort auf die aktuelle Frage und verbucht sie.

        `eingabe` ist ein String bei normalen Karten und eine Liste mit zwei
        Strings bei Triple-Karten.
        """
        if self.aktuelle_frage is None:
            raise RuntimeError("Es liegt keine aktive Frage vor")

        frage = self.aktuelle_frage
        card = frage.card
        gruppe = self._streak_gruppe(card)

        if card.is_triple:
            eingaben = list(eingabe) if isinstance(eingabe, (list, tuple)) else [eingabe]
            ok = card.pruefe(eingaben)
            loesung = card.volle_loesung()
            weitere: list[str] = []
        else:
            text = eingabe if isinstance(eingabe, str) else str(eingabe)
            ok = card.pruefe(text, frage.rueckwaerts)
            loesung = card.erwartet(frage.rueckwaerts)
            weitere = card.weitere_loesungen(text, frage.rueckwaerts) if ok else []

        if ok:
            # Richtig zählt nur für diese eine Karte - beim Triple müssen
            # alle drei Formen einzeln sitzen.
            gewinn, level_up = self.fortschritt.richtig([card.key])
            return Ergebnis(
                richtig=True,
                xp=gewinn,
                level_up=level_up,
                combo=self.fortschritt.current_combo,
                multiplikator=rules.combo_mul(self.fortschritt.current_combo),
                loesung=loesung,
                weitere=weitere,
            )

        # Nur ein Vertipper? Dann kommt die Karte wieder, aber die Combo
        # bleibt stehen. Bei Triple-Karten gilt das nicht: dort IST die
        # genaue Form die Aufgabe.
        if not card.is_triple:
            vergleich = tippfehler.vergleiche(
                text, card.akzeptierte_antworten(frage.rueckwaerts),
                self._fremde_antworten(card, frage.rueckwaerts),
            )
            if vergleich.fast:
                self.fortschritt.nochmal(gruppe)
                return Ergebnis(
                    richtig=False, fast=True,
                    combo=self.fortschritt.current_combo,
                    loesung=loesung, hinweis=vergleich.grund,
                )

        # Falsch setzt das ganze Paket zurück.
        self.fortschritt.falsch(gruppe)
        return Ergebnis(richtig=False, combo=0, loesung=loesung)

    def naechste_runde(self) -> bool:
        """Startet die Wiederholungsrunde. False heisst: Sitzung fertig."""
        fehler = self._fehlerkarten()
        if not fehler:
            return False
        for key in fehler:
            card = self._nach_key.get(key)
            if card is None:
                continue
            for k in self._streak_gruppe(card):
                self.fortschritt.streaks[k] = 0
        self.fortschritt.neue_runde()
        self.runde += 1
        return True

    def neustart(self) -> None:
        self.fortschritt.zuruecksetzen()
        self.runde = 1
        self.aktuelle_frage = None
        self._bias = self.rng.uniform(_BIAS_MIN, _BIAS_MAX)

    # -- Statistik ------------------------------------------------------------

    def statistik(self) -> dict:
        p = self.fortschritt
        schwerste = sorted(p.total_errors.items(), key=lambda x: x[1], reverse=True)
        return {
            "accuracy": p.accuracy,
            "richtig": p.total_correct,
            "falsch": p.total_wrong,
            "xp": p.xp,
            "level": p.level,
            "best_combo": p.best_combo,
            "runden": self.runde,
            "schwerste_karten": schwerste[:4],
        }
