"""ViewModel für Ordner und Lernsets.

Zuständig für Anlegen, Bearbeiten, Löschen, Verschieben und die
Fortschrittsanzeige je Lernset. Die Prozentzahl kommt aus derselben Quelle wie
der Lernbildschirm (LearningSession.fortschritt_zaehler).
"""
from __future__ import annotations

import uuid
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from lernapp import __version__
from lernapp.core.cards import TripleCard
from lernapp.core.import_export import dateiname_fuer, parse_text
from lernapp.netz import ki, lernset_ki
from lernapp.storage import dokumente
from lernapp.storage import local_storage as store

from . import arbeit
from .app_state import AppState


def _pfad_aus(url: str) -> Path:
    """QML liefert file:///C:/... - daraus einen echten Pfad machen."""
    if url.startswith("file:"):
        return Path(QUrl(url).toLocalFile())
    return Path(url)


class SetsViewModel(QObject):
    baumGeaendert = Signal()
    lernsetGewaehlt = Signal(str)
    fehler = Signal(str)
    hinweis = Signal(str)
    # Ergebnis der Vokabelerkennung: Text im Format der Zwischenablage plus
    # ein Satz darüber, was erkannt wurde.
    vokabelnErkannt = Signal(str, str)
    erkennungGeaendert = Signal()

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self._state = state
        self._aktives = ""
        self._erkennung_laeuft = False

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
        """Rohdaten für den Bearbeiten-Dialog."""
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
        """Legt an oder aktualisiert. Gibt die ID zurück, "" bei Fehler."""
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
        # Fortschritt bewusst behalten: ein versehentliches Löschen soll den
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

        Erzeugt über TripleCard aus dem Core, damit Anzeige und Speicherformat
        garantiert zusammenpassen - auch bei mehrwortigen Formen wie "had to".
        """
        formen = ((f1 or "").strip().lower(),
                  (f2 or "").strip().lower(),
                  (f3 or "").strip().lower())
        if not all(formen):
            self.fehler.emit("Bitte alle drei Formen ausfüllen")
            return []
        return [TripleCard(forms=formen, revealed=i).legacy_item() for i in (0, 1, 2)]

    # -- Import und Export ----------------------------------------------------

    @Slot(str, result=str)
    def standardDateiname(self, ls_id: str) -> str:
        _ordner, ls = self._state.finde_lernset(ls_id)
        return dateiname_fuer(ls["name"]) if ls else "Lernset.lernset.json"

    @Slot(str, str, result=bool)
    def exportiereLernset(self, ls_id: str, ziel_url: str) -> bool:
        _ordner, ls = self._state.finde_lernset(ls_id)
        if ls is None:
            self.fehler.emit("Lernset nicht gefunden")
            return False
        try:
            ziel = store.exportiere_lernset(
                ls["name"], ls["items"], _pfad_aus(ziel_url), __version__)
        except (OSError, ValueError) as problem:
            self.fehler.emit(f"Export fehlgeschlagen: {problem}")
            return False
        self.hinweis.emit(f"Exportiert nach {ziel.name}")
        return True

    @Slot(str, str, result=str)
    def importiereLernset(self, quell_url: str, ordner: str) -> str:
        try:
            name, items = store.importiere_lernset(_pfad_aus(quell_url))
        except ValueError as problem:
            self.fehler.emit(str(problem))
            return ""
        ziel = ordner if ordner in self._state.folders else self._erster_ordner()
        neu = {"id": str(uuid.uuid4()), "name": name, "items": items}
        self._state.folders[ziel]["lernsets"].append(neu)
        self._state.save_data()
        self.baumGeaendert.emit()
        self.hinweis.emit(f"„{name}“ importiert · {len(items)} Karten")
        return neu["id"]

    # -- Vokabeln aus einem Dokument ------------------------------------------

    @Property(bool, notify=erkennungGeaendert)
    def erkennungLaeuft(self) -> bool:
        return self._erkennung_laeuft

    @Property(bool, notify=erkennungGeaendert)
    def kiVerfuegbar(self) -> bool:
        """Ohne eingerichteten Zugang bleibt der Knopf aus, statt zu scheitern."""
        return ki.aus_umgebung().bereit

    @Slot(str)
    def ausDokument(self, quell_url: str) -> None:
        """PDF oder Textdatei einlesen und die Vokabeln erkennen lassen.

        Das Ergebnis geht als Text ins vorhandene Einfügefeld - und damit
        durch dieselbe Vorschau wie ein von Hand eingefügter Text. Ein Modell,
        das sich irrt, kann so nichts speichern, was der Nutzer nicht gesehen
        hat.
        """
        if self._erkennung_laeuft:
            return
        pfad = _pfad_aus(quell_url)
        self._erkennung_laeuft = True
        self.erkennungGeaendert.emit()

        def arbeiten():
            text = dokumente.lies_text(pfad)
            return lernset_ki.erkenne_vokabeln(ki.aus_umgebung(), text)

        arbeit.starte(arbeiten, self._vokabeln_da, self._erkennung_fehler,
                      (dokumente.DokumentFehler, ki.KIFehler))

    def _vokabeln_da(self, vorschlag) -> None:
        self._erkennung_laeuft = False
        self.erkennungGeaendert.emit()
        self.vokabelnErkannt.emit(vorschlag.text, vorschlag.zusammenfassung())

    def _erkennung_fehler(self, text: str) -> None:
        self._erkennung_laeuft = False
        self.erkennungGeaendert.emit()
        self.fehler.emit(text)

    @Slot(str, result="QVariantMap")
    def textVorschau(self, text: str) -> dict:
        """Zeigt, was ein Textimport ergäbe - ohne etwas zu speichern."""
        ergebnis = parse_text(text)
        return {
            "ok": ergebnis.ok,
            "zusammenfassung": ergebnis.zusammenfassung(),
            "normale": ergebnis.normale,
            "pakete": ergebnis.pakete,
            "einheiten": ergebnis.einheiten,
            "trenner": ergebnis.trenner,
            "probleme": [
                {"zeile": p.zeile, "text": p.text, "grund": p.grund}
                for p in ergebnis.probleme[:8]
            ],
        }

    @Slot(str, result="QVariantList")
    def textKarten(self, text: str) -> list:
        """Die Karten eines Textimports - für den Lernset-Dialog."""
        return parse_text(text).items

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
