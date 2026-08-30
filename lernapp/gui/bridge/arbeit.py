"""Arbeit im Hintergrundfaden, Ergebnis im Hauptfaden.

Jeder Netzzugriff der App läuft hierüber. Zwei Regeln, die dahinterstehen:

- Ein langsamer Server darf die Oberfläche nicht einfrieren.
- Geschrieben wird **nur im Hauptfaden**. Der Arbeitsfaden holt und prüft,
  das Ergebnis kommt per Signal zurück, und erst dort werden Dateien
  angefasst. Qt stellt die Zustellung über Fadengrenzen selbst sicher.
"""
from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from lernapp.storage import protokoll

_log = logging.getLogger(protokoll.LOGGER_NAME)


class _Signale(QObject):
    """QRunnable ist kein QObject und kann selbst keine Signale senden."""

    fertig = Signal(object)
    fehlgeschlagen = Signal(str)


class Auftrag(QRunnable):
    """Führt `arbeit` im Arbeitsfaden aus und meldet das Ergebnis.

    `erwartet` sind die Ausnahmen, deren Text dem Nutzer gezeigt werden darf.
    Alles andere gilt als Fehler im Programm: es landet im Protokoll, und der
    Nutzer bekommt einen allgemeinen Satz statt eines Tracebacks.
    """

    def __init__(self, arbeit: Callable[[], object],
                 erwartet: tuple[type[Exception], ...]) -> None:
        super().__init__()
        self._arbeit = arbeit
        self._erwartet = erwartet
        self.signale = _Signale()

    def run(self) -> None:  # läuft im Arbeitsfaden
        try:
            self.signale.fertig.emit(self._arbeit())
        except self._erwartet as grund:
            self.signale.fehlgeschlagen.emit(str(grund))
        except Exception:
            _log.exception("Unerwarteter Fehler in einem Hintergrundauftrag")
            self.signale.fehlgeschlagen.emit(
                "Etwas ist schiefgelaufen. Bitte später erneut versuchen."
            )


def starte(arbeit: Callable[[], object], beim_erfolg: Callable[[object], None],
           beim_fehler: Callable[[str], None],
           erwartet: tuple[type[Exception], ...],
           synchron: bool = False) -> None:
    """Auftrag einreihen - oder mit `synchron=True` sofort ausführen.

    Der synchrone Weg ist für Tests: sonst müsste jeder Test auf einen
    Thread-Pool warten, und ein hängender Test ist schlimmer als gar keiner.
    """
    if synchron:
        try:
            beim_erfolg(arbeit())
        except erwartet as grund:
            beim_fehler(str(grund))
        return

    auftrag = Auftrag(arbeit, erwartet)
    auftrag.signale.fertig.connect(beim_erfolg)
    auftrag.signale.fehlgeschlagen.connect(beim_fehler)
    QThreadPool.globalInstance().start(auftrag)
