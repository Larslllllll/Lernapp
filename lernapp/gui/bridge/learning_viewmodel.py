"""ViewModel der Lernansicht.

Übersetzt zwischen QML und lernapp.core.learning_engine. Enthält bewusst
keine Lernregeln: XP, Combo, Kartenauswahl, Runden und Triple-Logik bleiben
vollständig im Core. Hier wird nur koordiniert und für die Anzeige
aufbereitet.
"""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from lernapp.core import rules
from lernapp.core.cards import parse_items
from lernapp.core.learning_engine import LearningSession, SessionZustand
from lernapp.platform_services import dienste

from .app_state import AppState

# Feedback-Arten, die QML kennt. Reine Darstellungsklassifikation.
NEUTRAL = "neutral"
RICHTIG = "richtig"
FALSCH = "falsch"
LEVELUP = "levelup"
RUNDE = "runde"


class LearningViewModel(QObject):
    zustandGeaendert = Signal()
    frageGeaendert = Signal()
    feedbackGeaendert = Signal()
    lernsetGeaendert = Signal()
    comboPuls = Signal()
    levelUp = Signal(int)
    fortschrittGespeichert = Signal(str)

    def __init__(self, state: AppState, richtung: str) -> None:
        super().__init__()
        self._state = state
        self._richtung = richtung
        self._session: LearningSession | None = None
        self._ls_id = ""
        self._ls_name = ""
        self._frage_typ = "leer"
        self._frage_text = ""
        self._slots: list = []
        self._feedback = ""
        self._feedback_art = NEUTRAL
        self._gesperrt = False
        self._statistik: dict = {}

    # -- Lernset wählen ------------------------------------------------------

    @Slot(str)
    def waehleLernset(self, ls_id: str) -> None:
        ordner, ls = self._state.finde_lernset(ls_id)
        if ls is None:
            return
        self._ls_id = ls["id"]
        self._ls_name = ls["name"]
        self._session = LearningSession(
            parse_items(ls["items"]),
            fortschritt=self._state.fortschritt_von(ls["id"]),
            richtung=self._richtung,
        )
        self._statistik = {}
        self._setze_feedback("", NEUTRAL)
        self.lernsetGeaendert.emit()
        self.weiter()

    @Slot()
    def lernsetNeuLaden(self) -> None:
        """Nach dem Bearbeiten eines Lernsets die Sitzung neu aufbauen."""
        if self._ls_id:
            self.waehleLernset(self._ls_id)

    @Property(str, notify=lernsetGeaendert)
    def lernsetId(self) -> str:
        return self._ls_id

    @Property(str, notify=lernsetGeaendert)
    def lernsetName(self) -> str:
        return self._ls_name

    @Property(bool, notify=lernsetGeaendert)
    def hatLernset(self) -> bool:
        return self._session is not None

    # -- Richtung -------------------------------------------------------------

    @Slot(str)
    def setzeRichtung(self, richtung: str) -> None:
        self._richtung = richtung
        if self._session is not None:
            self._session.richtung = richtung

    # -- Anzeigewerte ---------------------------------------------------------

    def _z(self) -> dict:
        if self._session is None:
            return {}
        p = self._session.fortschritt
        level, seit, spanne = rules.level_fortschritt(p.xp)
        gelernt, gesamt = self._session.fortschritt_zaehler()
        return {
            "xp": p.xp,
            "level": level,
            "levelAnteil": 1.0 if spanne is None else seit / spanne,
            "xpBisLevel": 0 if spanne is None else rules.LEVEL_XP[level],
            "maxLevel": spanne is None,
            "combo": p.current_combo,
            "bestCombo": p.best_combo,
            "gelernt": gelernt,
            "gesamt": gesamt,
            "anteil": gelernt / max(1, gesamt),
            "runde": self._session.runde,
        }

    @Property(int, notify=zustandGeaendert)
    def xp(self) -> int:
        return self._z().get("xp", 0)

    @Property(int, notify=zustandGeaendert)
    def level(self) -> int:
        return self._z().get("level", 1)

    @Property(float, notify=zustandGeaendert)
    def levelAnteil(self) -> float:
        return self._z().get("levelAnteil", 0.0)

    @Property(int, notify=zustandGeaendert)
    def xpBisLevel(self) -> int:
        return self._z().get("xpBisLevel", 0)

    @Property(bool, notify=zustandGeaendert)
    def maxLevel(self) -> bool:
        return self._z().get("maxLevel", False)

    @Property(int, notify=zustandGeaendert)
    def combo(self) -> int:
        return self._z().get("combo", 0)

    @Property(int, notify=zustandGeaendert)
    def bestCombo(self) -> int:
        return self._z().get("bestCombo", 0)

    @Property(int, notify=zustandGeaendert)
    def gelernt(self) -> int:
        return self._z().get("gelernt", 0)

    @Property(int, notify=zustandGeaendert)
    def gesamt(self) -> int:
        return self._z().get("gesamt", 0)

    @Property(float, notify=zustandGeaendert)
    def anteil(self) -> float:
        return self._z().get("anteil", 0.0)

    @Property(int, notify=zustandGeaendert)
    def runde(self) -> int:
        return self._z().get("runde", 1)

    # -- Aktuelle Frage -------------------------------------------------------

    @Property(str, notify=frageGeaendert)
    def frageTyp(self) -> str:
        """"normal" | "triple" | "fertig" | "leer\""""
        return self._frage_typ

    @Property(str, notify=frageGeaendert)
    def frageText(self) -> str:
        return self._frage_text

    @Property("QVariantList", notify=frageGeaendert)
    def slots(self) -> list:
        return self._slots

    @Property(bool, notify=frageGeaendert)
    def rueckwaerts(self) -> bool:
        f = self._session.aktuelle_frage if self._session else None
        return bool(f and f.rueckwaerts)

    @Property("QVariantMap", notify=frageGeaendert)
    def statistik(self) -> dict:
        return self._statistik

    # -- Feedback -------------------------------------------------------------

    @Property(str, notify=feedbackGeaendert)
    def feedbackText(self) -> str:
        return self._feedback

    @Property(str, notify=feedbackGeaendert)
    def feedbackArt(self) -> str:
        return self._feedback_art

    @Property(bool, notify=feedbackGeaendert)
    def gesperrt(self) -> bool:
        return self._gesperrt

    def _setze_feedback(self, text: str, art: str) -> None:
        self._feedback = text
        self._feedback_art = art
        self.feedbackGeaendert.emit()

    # -- Ablauf ---------------------------------------------------------------

    @Slot()
    def weiter(self) -> None:
        if self._session is None:
            return
        self._gesperrt = False
        frage = self._session.naechste_frage()

        if frage is None:
            if self._session.zustand == SessionZustand.RUNDE_FERTIG and self._session.naechste_runde():
                offen = len(self._session.offene_keys)
                self._setze_feedback(
                    f"Runde {self._session.runde} · {offen} schwache Karte"
                    f"{'n' if offen != 1 else ''}", RUNDE)
                self._speichern()
                self.zustandGeaendert.emit()
                self.weiter()
                return
            self._zeige_statistik()
            return

        if frage.ist_triple:
            self._frage_typ = "triple"
            self._frage_text = ""
            self._slots = [{"text": text or "", "eingabe": text is None}
                           for _i, text in frage.card.slots()]
        else:
            self._frage_typ = "normal"
            self._frage_text = frage.anzeige
            self._slots = []

        if self._feedback_art != RUNDE:
            self._setze_feedback("", NEUTRAL)
        self.frageGeaendert.emit()
        self.zustandGeaendert.emit()

    @Slot("QVariantList")
    def pruefe(self, eingaben: list) -> None:
        if self._session is None or self._gesperrt:
            return
        if self._session.aktuelle_frage is None:
            return
        werte = [str(e) for e in eingaben]
        if not werte:
            return

        self._gesperrt = True
        ergebnis = self._session.antworte(werte if len(werte) > 1 else werte[0])
        if self._state.settings.get("sound", True):
            dienste().spiele_ton(ergebnis.richtig)

        if ergebnis.richtig:
            mult = f"  ×{ergebnis.multiplikator:g}" if ergebnis.multiplikator > 1 else ""
            auch = f"   ·   auch: {', '.join(ergebnis.weitere)}" if ergebnis.weitere else ""
            if ergebnis.level_up:
                self._setze_feedback(
                    f"Level {self._session.fortschritt.level} erreicht   +{ergebnis.xp} XP{mult}",
                    LEVELUP)
                self.levelUp.emit(self._session.fortschritt.level)
            else:
                self._setze_feedback(f"Richtig   +{ergebnis.xp} XP{mult}{auch}", RICHTIG)
            self.comboPuls.emit()
        else:
            self._setze_feedback(f"Richtig wäre:  {ergebnis.loesung}", FALSCH)

        self._speichern()
        self.zustandGeaendert.emit()

    def _zeige_statistik(self) -> None:
        s = self._session.statistik()
        self._statistik = {
            "accuracy": round(s["accuracy"] * 100),
            "richtig": s["richtig"],
            "falsch": s["falsch"],
            "level": s["level"],
            "xp": s["xp"],
            "bestCombo": s["best_combo"],
            "runden": s["runden"],
            "schwerste": [{"frage": q, "anzahl": n} for q, n in s["schwerste_karten"]],
        }
        self._frage_typ = "fertig"
        self._frage_text = ""
        self._slots = []
        self._setze_feedback("", NEUTRAL)
        self.frageGeaendert.emit()
        self.zustandGeaendert.emit()

    @Slot()
    def neustart(self) -> None:
        if self._session is None:
            return
        self._session.neustart()
        self._statistik = {}
        self._setze_feedback("", NEUTRAL)
        self._speichern()
        self.weiter()

    @Slot()
    def fortschrittLoeschen(self) -> None:
        """Setzt nur das aktuelle Lernset zurück - wie in der Vorgängerversion."""
        if self._session is None:
            return
        self._session.neustart()
        self._statistik = {}
        self._speichern()
        self._setze_feedback("Fortschritt dieses Lernsets gelöscht", NEUTRAL)
        self.weiter()

    def _speichern(self) -> None:
        if self._session is None or not self._ls_id:
            return
        self._state.speichere_fortschritt(self._ls_id, self._session.fortschritt)
        self.fortschrittGespeichert.emit(self._ls_id)
