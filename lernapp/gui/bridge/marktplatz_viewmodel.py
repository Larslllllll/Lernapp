"""Marktplatz: Lernsets direkt aus dem Netz übernehmen.

Das Laden läuft in einem Arbeitsfaden aus dem globalen QThreadPool. Ein
langsamer Server darf die Oberfläche nicht einfrieren - und ein
fehlgeschlagener Abruf darf das Lernen nicht blockieren: er meldet sich und
sonst passiert nichts.

Geschrieben wird ausschliesslich im Hauptfaden. Der Arbeitsfaden lädt und
prüft, das Ergebnis kommt per Signal zurück, und erst der Hauptfaden fasst
data.json an.
"""
from __future__ import annotations

import logging
import uuid

from PySide6.QtCore import Property, QObject, QRunnable, QThreadPool, Signal, Slot

from lernapp.netz import marktplatz
from lernapp.netz.marktplatz import Eintrag, Katalog, MarktplatzFehler
from lernapp.storage import protokoll

from .app_state import AppState

_log = logging.getLogger(protokoll.LOGGER_NAME)


class _Signale(QObject):
    """QRunnable ist kein QObject und kann selbst keine Signale senden."""

    fertig = Signal(object)
    fehlgeschlagen = Signal(str)


class _Auftrag(QRunnable):
    def __init__(self, arbeit) -> None:
        super().__init__()
        self._arbeit = arbeit
        self.signale = _Signale()

    def run(self) -> None:  # läuft im Arbeitsfaden
        try:
            self.signale.fertig.emit(self._arbeit())
        except MarktplatzFehler as grund:
            self.signale.fehlgeschlagen.emit(str(grund))
        except Exception:
            # Alles Unerwartete gehört ins Protokoll, aber der Nutzer soll
            # keinen Traceback sehen - und die App darf nicht sterben, nur
            # weil der Marktplatz sich seltsam verhält.
            _log.exception("Unerwarteter Fehler im Marktplatz")
            self.signale.fehlgeschlagen.emit(
                "Beim Laden ist etwas schiefgelaufen. Bitte später erneut versuchen."
            )


class MarktplatzViewModel(QObject):
    laedtGeaendert = Signal()
    eintraegeGeaendert = Signal()
    fehler = Signal(str)
    hinweis = Signal(str)
    uebernommen = Signal(str)

    def __init__(self, state: AppState, lader=marktplatz.lade_ueber_netz,
                 synchron: bool = False) -> None:
        """`lader` und `synchron` sind für Tests gedacht.

        Mit `synchron=True` läuft die Arbeit im aufrufenden Faden, damit ein
        Test nicht auf einen Thread-Pool warten muss.
        """
        super().__init__()
        self._state = state
        self._lader = lader
        self._synchron = synchron
        self._katalog: Katalog | None = None
        self._laedt = False
        self._geladen_einmal = False

    # -- Eigenschaften --------------------------------------------------------

    @Property(bool, notify=laedtGeaendert)
    def laedt(self) -> bool:
        return self._laedt

    @Property(str, notify=eintraegeGeaendert)
    def aktualisiertAm(self) -> str:
        return self._katalog.aktualisiert_am if self._katalog else ""

    @Property("QVariantList", notify=eintraegeGeaendert)
    def eintraege(self) -> list:
        if self._katalog is None:
            return []
        vorhanden = {ls["name"].strip().casefold()
                     for _, ls in self._state.alle_lernsets()}
        return [{
            "id": e.id,
            "name": e.name,
            "fach": e.fach,
            "karten": e.karten,
            "vorhanden": e.name.strip().casefold() in vorhanden,
        } for e in self._katalog.eintraege]

    @Property("QVariantList", notify=eintraegeGeaendert)
    def faecher(self) -> list:
        return list(self._katalog.faecher()) if self._katalog else []

    # -- Aktionen -------------------------------------------------------------

    @Slot()
    def aktualisieren(self) -> None:
        """Katalog holen. Ein zweiter Aufruf während des Ladens tut nichts."""
        if self._laedt:
            return
        self._setze_laedt(True)
        self._starte(
            lambda: marktplatz.lade_katalog(self._lader),
            self._katalog_da,
        )

    @Slot()
    def einmalLaden(self) -> None:
        """Beim ersten Öffnen laden, danach den Katalog behalten."""
        if not self._geladen_einmal:
            self.aktualisieren()

    @Slot(str)
    def uebernehmen(self, eintrag_id: str) -> None:
        eintrag = self._finde(eintrag_id)
        if eintrag is None:
            self.fehler.emit("Dieses Lernset steht nicht mehr im Verzeichnis.")
            return
        if self._laedt:
            return
        self._setze_laedt(True)
        self._starte(
            lambda: (eintrag, *marktplatz.lade_lernset(eintrag, self._lader)),
            self._lernset_da,
        )

    # -- Innereien ------------------------------------------------------------

    def _finde(self, eintrag_id: str) -> Eintrag | None:
        if self._katalog is None:
            return None
        for eintrag in self._katalog.eintraege:
            if eintrag.id == eintrag_id:
                return eintrag
        return None

    def _starte(self, arbeit, beim_erfolg) -> None:
        if self._synchron:
            try:
                beim_erfolg(arbeit())
            except MarktplatzFehler as grund:
                self._fehlgeschlagen(str(grund))
            return
        auftrag = _Auftrag(arbeit)
        auftrag.signale.fertig.connect(beim_erfolg)
        auftrag.signale.fehlgeschlagen.connect(self._fehlgeschlagen)
        QThreadPool.globalInstance().start(auftrag)

    def _setze_laedt(self, wert: bool) -> None:
        if self._laedt != wert:
            self._laedt = wert
            self.laedtGeaendert.emit()

    def _fehlgeschlagen(self, text: str) -> None:
        self._setze_laedt(False)
        self.fehler.emit(text)

    def _katalog_da(self, katalog: Katalog) -> None:
        self._katalog = katalog
        self._geladen_einmal = True
        self._setze_laedt(False)
        self.eintraegeGeaendert.emit()

    def _lernset_da(self, ergebnis: tuple) -> None:
        """Erst hier wird geschrieben - im Hauptfaden."""
        eintrag, name, items = ergebnis
        ordner = self._ordner_fuer(eintrag.fach)
        neu = {"id": str(uuid.uuid4()), "name": name, "items": items}
        self._state.folders[ordner]["lernsets"].append(neu)
        self._state.save_data()
        self._setze_laedt(False)
        self.eintraegeGeaendert.emit()
        self.uebernommen.emit(neu["id"])
        self.hinweis.emit(f"„{name}“ übernommen · {len(items)} Karten in {ordner}")

    def _ordner_fuer(self, fach: str) -> str:
        """Passenden Ordner finden oder anlegen.

        Das Fach aus dem Marktplatz ist die naheliegende Ablage - so muss
        niemand vor dem Herunterladen entscheiden, wohin das Set soll.
        Gross- und Kleinschreibung wird dabei ignoriert, damit nicht
        „englisch" neben „Englisch" entsteht.
        """
        for vorhanden in self._state.folders:
            if vorhanden.strip().casefold() == fach.strip().casefold():
                return vorhanden
        self._state.folders[fach] = {"lernsets": []}
        return fach
