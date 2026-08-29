"""Fortschritt eines Lernsets - ohne GUI, ohne Datei-I/O.

Zwei Trennungen, die die Vorgaengerversion nicht hatte:

  round_errors  vs  total_errors
      round_errors steuert Wiederholung und Kartengewichtung und wird zu
      Rundenbeginn geleert. total_errors ist die Historie fuer die Statistik
      und bleibt erhalten.

  current_combo vs  best_combo
      current_combo faellt bei einer falschen Antwort auf 0. best_combo haelt
      den Hoechstwert fest.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import rules

SCHEMA_VERSION = 2


@dataclass
class SetProgress:
    xp: int = 0
    total_correct: int = 0
    total_wrong: int = 0
    current_combo: int = 0
    best_combo: int = 0
    round_errors: dict[str, int] = field(default_factory=dict)
    total_errors: dict[str, int] = field(default_factory=dict)
    streaks: dict[str, int] = field(default_factory=dict)

    # ── Regeln ────────────────────────────────────────────────────────────────

    @property
    def level(self) -> int:
        return rules.get_level(self.xp)

    @property
    def accuracy(self) -> float:
        gesamt = self.total_correct + self.total_wrong
        return self.total_correct / gesamt if gesamt else 0.0

    def richtig(self, keys: list[str]) -> tuple[int, bool]:
        """Verbucht eine richtige Antwort. Gibt (xp_gewinn, level_up) zurueck.

        `keys` sind alle Streak-Schluessel, die mitziehen - bei einem Triple
        also alle drei Karten des Pakets.
        """
        vorher = self.level
        self.current_combo += 1
        self.best_combo = max(self.best_combo, self.current_combo)
        self.total_correct += 1
        for k in keys:
            self.streaks[k] = self.streaks.get(k, 0) + 1
        gewinn = rules.xp_gain(self.streaks[keys[0]], self.current_combo)
        self.xp += gewinn
        return gewinn, self.level > vorher

    def falsch(self, keys: list[str]) -> None:
        """Verbucht eine falsche Antwort und setzt das ganze Paket zurueck."""
        self.current_combo = 0
        self.total_wrong += 1
        for k in keys:
            self.streaks[k] = 0
        haupt = keys[0]
        self.round_errors[haupt] = self.round_errors.get(haupt, 0) + 1
        self.total_errors[haupt] = self.total_errors.get(haupt, 0) + 1

    def neue_runde(self) -> None:
        """Rundenwechsel: nur die Rundenfehler und die Combo werden geleert."""
        self.round_errors.clear()
        self.current_combo = 0

    def zuruecksetzen(self) -> None:
        """Kompletter Neustart des Lernsets. best_combo bleibt als Rekord."""
        self.xp = 0
        self.total_correct = 0
        self.total_wrong = 0
        self.current_combo = 0
        self.round_errors.clear()
        self.total_errors.clear()
        for k in self.streaks:
            self.streaks[k] = 0

    def gewicht(self, key: str) -> int:
        """Auswahlgewicht einer Karte - haeufige Fehler kommen oefter dran."""
        return max(1, self.round_errors.get(key, 0) * 3 + 1)

    # ── Serialisierung ────────────────────────────────────────────────────────

    @classmethod
    def from_legacy(cls, roh: dict) -> "SetProgress":
        """Liest altes UND neues Format.

        Altes Format kannte nur `errors` (Rundenfehler) und `combo`
        (laufende Combo). Beides wird uebernommen, ohne Informationsverlust:
        `errors` fuellt zusaetzlich total_errors, `combo` wird als bisheriger
        Rekord nach best_combo uebernommen. Die laufende Combo startet bei 0 -
        ein Multiplikator darf einen Programmneustart nicht ueberleben.
        """
        errors = dict(roh.get("errors", {}))
        return cls(
            xp=roh.get("xp", 0),
            total_correct=roh.get("correct", 0),
            total_wrong=roh.get("wrong", 0),
            current_combo=0,
            best_combo=roh.get("best_combo", roh.get("combo", 0)),
            round_errors=errors,
            total_errors=dict(roh.get("total_errors", errors)),
            streaks=dict(roh.get("streaks", {})),
        )

    def to_legacy(self) -> dict:
        """Schreibt additiv: alte Schluessel bleiben erhalten, neue kommen dazu.

        Dadurch kann eine aeltere Programmversion die Datei weiterhin lesen.
        """
        return {
            "schema_version": SCHEMA_VERSION,
            "xp": self.xp,
            "correct": self.total_correct,
            "wrong": self.total_wrong,
            "combo": self.current_combo,
            "errors": dict(self.round_errors),
            "streaks": dict(self.streaks),
            "best_combo": self.best_combo,
            "total_errors": dict(self.total_errors),
        }
