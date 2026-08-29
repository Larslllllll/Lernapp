"""ViewModel fuer Ordner und Lernsets.

Zustaendig fuer Anlegen, Bearbeiten, Loeschen, Verschieben und die
Fortschrittsanzeige je Lernset. Die Prozentzahl kommt aus derselben Quelle wie
der Lernbildschirm (LearningSession.fortschritt_zaehler).
"""
from __future__ import annotations

import uuid

from PySide6.QtCore import Property, QObject, Signal, Slot

from lernapp.core.cards import TripleCard

from .app_state import AppState


class SetsViewModel(QObject):
    baumGeaendert = Signal()
    lernsetGewaehlt = Signal(str)
    fehler = Signal(str)

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self._state = state
        self._aktives = ""

    # -- Baum -----------------------------------------------------------------

    @Property("QVariantList", notify=baumGeaendert)
    def ordner(self) -> list:
        ergebnis = []
        for name, fdata in self._state.folders.items():
            eintraege = []
            for ls in fdata.get("lernsets", []):
                gelernt, gesamt = self._state.zaehler_von(ls["id"], ls["items"])
                eintraege.append({
                    "id": ls["id"],
                    "name": ls["name"],
                    "karten": gesamt,
                    "gelernt": gelernt,
                    "prozent": int(gelernt / max(1, gesamt) * 100),
                    "aktiv": ls["id"] == self._aktives,
                })
            ergebnis.append({"name": name, "lernsets": eintraege})
        return ergebnis

    @Property(str, notify=baumGeaendert)
    def aktivesLernset(self) -> str:
        return self._aktives

    @Slot(str)
    def waehle(self, ls_id: str) -> None:
        _ordner, ls = self._state.finde_lernset(ls_id)
        if ls is None:
            return
        self._aktives = ls_id
        self.baumGeaendert.emit()
        self.lernsetGewaehlt.emit(ls_id)

    @Slot()
    def aktualisiere(self) -> None:
        """Nach dem Lernen die Prozentzahlen neu berechnen."""
        self.baumGeaendert.emit()

    # -- Ordner ---------------------------------------------------------------

    @Slot(str, result=bool)
    def ordnerAnlegen(self, name: str) -> bool:
        name = (name or "").strip()
        if not name:
            return False
        if name in self._state.folders:
            self.fehler.emit(f"Ordner „{name}“ existiert bereits")
            return False
        self._state.folders[name] = {"lernsets": []}
        self._state.save_data()
        self.baumGeaendert.emit()
        return True

    @Slot(str, result=bool)
    def ordnerLoeschen(self, name: str) -> bool:
        fdata = self._state.folders.get(name)
        if fdata is None:
            return False
        if fdata.get("lernsets"):
            self.fehler.emit("Ordner ist nicht leer")
            return False
        del self._state.folders[name]
        self._state.save_data()
        self.baumGeaendert.emit()
        return True

    # -- Lernsets -------------------------------------------------------------

    @Slot(str, result="QVariantMap")
    def lernsetLaden(self, ls_id: str) -> dict:
        """Rohdaten fuer den Bearbeiten-Dialog."""
        ordner, ls = self._state.finde_lernset(ls_id)
        if ls is None:
            return {}
        return {
            "id": ls["id"],
            "name": ls["name"],
            "ordner": ordner,
            "items": [dict(i) for i in ls["items"]],
        }

    @Slot(str, str, "QVariantList", result=str)
    def lernsetSpeichern(self, ls_id: str, name: str, items: list) -> str:
        """Legt an oder aktualisiert. Gibt die ID zurueck, "" bei Fehler."""
        name = (name or "").strip()
        sauber = self._items_saeubern(items)
        if not name:
            self.fehler.emit("Bitte einen Namen angeben")
            return ""
        if not sauber:
            self.fehler.emit("Das Lernset enthält keine Karten")
            return ""

        if ls_id:
            ordner, ls = self._state.finde_lernset(ls_id)
            if ls is not None:
                ls["name"] = name
                ls["items"] = sauber
                self._state.save_data()
                self.baumGeaendert.emit()
                return ls_id

        ordner = self._erster_ordner()
        neu = {"id": str(uuid.uuid4()), "name": name, "items": sauber}
        self._state.folders[ordner]["lernsets"].append(neu)
        self._state.save_data()
        self.baumGeaendert.emit()
        return neu["id"]

    @Slot(str, str, "QVariantList", result=str)
    def lernsetAnlegenIn(self, ordner: str, name: str, items: list) -> str:
        name = (name or "").strip()
        sauber = self._items_saeubern(items)
        if not name or not sauber or ordner not in self._state.folders:
            self.fehler.emit("Name und mindestens eine Karte sind nötig")
            return ""
        neu = {"id": str(uuid.uuid4()), "name": name, "items": sauber}
        self._state.folders[ordner]["lernsets"].append(neu)
        self._state.save_data()
        self.baumGeaendert.emit()
        return neu["id"]

    @Slot(str, result=bool)
    def lernsetLoeschen(self, ls_id: str) -> bool:
        ordner, ls = self._state.finde_lernset(ls_id)
        if ls is None:
            return False
        liste = self._state.folders[ordner]["lernsets"]
        self._state.folders[ordner]["lernsets"] = [x for x in liste if x["id"] != ls_id]
        # Fortschritt bewusst behalten: ein versehentliches Loeschen soll den
        # gesammelten XP-Stand nicht mitnehmen.
        if self._aktives == ls_id:
            self._aktives = ""
        self._state.save_data()
        self.baumGeaendert.emit()
        return True

    @Slot(str, str, result=bool)
    def lernsetVerschieben(self, ls_id: str, ziel_ordner: str) -> bool:
        quelle, ls = self._state.finde_lernset(ls_id)
        if ls is None or ziel_ordner not in self._state.folders or quelle == ziel_ordner:
            return False
        self._state.folders[quelle]["lernsets"] = [
            x for x in self._state.folders[quelle]["lernsets"] if x["id"] != ls_id]
        self._state.folders[ziel_ordner]["lernsets"].append(ls)
        self._state.save_data()
        self.baumGeaendert.emit()
        return True

    @Property("QVariantList", notify=baumGeaendert)
    def ordnerNamen(self) -> list:
        return list(self._state.folders.keys())

    # -- Karten bauen ---------------------------------------------------------

    @Slot(str, str, str, result="QVariantList")
    def tripleKarten(self, f1: str, f2: str, f3: str) -> list:
        """Drei Karten eines Verbpakets.

        Erzeugt ueber TripleCard aus dem Core, damit Anzeige und Speicherformat
        garantiert zusammenpassen - auch bei mehrwortigen Formen wie "had to".
        """
        formen = ((f1 or "").strip().lower(),
                  (f2 or "").strip().lower(),
                  (f3 or "").strip().lower())
        if not all(formen):
            self.fehler.emit("Bitte alle drei Formen ausfüllen")
            return []
        return [TripleCard(forms=formen, revealed=i).legacy_item() for i in (0, 1, 2)]

    # -- Hilfen ---------------------------------------------------------------

    def _erster_ordner(self) -> str:
        if not self._state.folders:
            self._state.folders["Meine Lernsets"] = {"lernsets": []}
        return next(iter(self._state.folders))

    @staticmethod
    def _items_saeubern(items: list) -> list[dict]:
        sauber = []
        for it in items or []:
            q = str(it.get("q", "")).strip()
            a = str(it.get("a", "")).strip()
            if q and a:
                sauber.append({"q": q, "a": a})
        return sauber
