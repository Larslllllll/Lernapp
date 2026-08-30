"""Protokolldatei und Absturzprotokoll.

Vorher hinterliess ein Absturz beim Nutzer keine Spur: kein Log, kein
Excepthook, und im gebauten Bundle gibt es keine Konsole, auf der ein
Traceback landen könnte. Ein Klassenkamerad konnte einen Fehler also gar nicht
melden.

Zwei Zusagen, die dieses Modul einhält:

  Nichts Persönliches im Log
      Keine Antworten, keine Vokabelinhalte. Tracebacks nennen aber immer den
      Installationsort, und der enthält unter Windows den Benutzernamen —
      deshalb ersetzt ``anonymisiere`` das Benutzerverzeichnis durch ``~``.
      Der Filter hängt am Handler, es kommt also nichts daran vorbei.

  Nichts wird verschickt
      Das Log bleibt lokal. Wer es Lars schicken will, tut das selbst.

Ein kaputtes Log darf das Lernen nie verhindern: schlägt die Einrichtung fehl,
läuft die App ohne Datei weiter.
"""
from __future__ import annotations

import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import paths

LOGGER_NAME = "lernapp"
DATEINAME = "lernapp.log"

# Klein gedeckelt: das Log ist eine Fehlermeldung zum Verschicken, kein
# Archiv. 256 KB plus zwei Backups sind auch per Chat noch zumutbar.
MAX_BYTES = 256 * 1024
ANZAHL_BACKUPS = 2

_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
_ZEITFORMAT = "%Y-%m-%d %H:%M:%S"

# Der eigene Handler wird gemerkt, statt ihn später aus ``logger.handlers`` zu
# fischen: dort hängen unter Umständen fremde Handler (pytest tut das), die uns
# nicht gehören und die wir weder zählen noch schliessen dürfen.
_handler: logging.Handler | None = None
_pfad: Path | None = None


def logs_verzeichnis(basis: Path | None = None) -> Path:
    return (basis or paths.datenverzeichnis()) / "logs"


def log_datei(basis: Path | None = None) -> Path:
    return logs_verzeichnis(basis) / DATEINAME


# -- Anonymisierung -----------------------------------------------------------

def anonymisiere(text: str) -> str:
    """Ersetzt das Benutzerverzeichnis durch ``~``.

    Beide Trennzeichen und beide Schreibweisen, weil derselbe Pfad mal mit
    Backslash und mal als ``C:/Users/...`` auftaucht und der Vergleich unter
    Windows ohnehin gross-klein-egal ist.
    """
    heim = str(Path.home())
    ergebnis = text
    for variante in {heim, heim.replace("\\", "/")}:
        ergebnis = _ersetze_ohne_gross_klein(ergebnis, variante, "~")
    return ergebnis


def _ersetze_ohne_gross_klein(text: str, suchen: str, ersatz: str) -> str:
    if not suchen:
        return text
    klein_text, klein_suchen = text.lower(), suchen.lower()
    teile: list[str] = []
    position = 0
    while True:
        treffer = klein_text.find(klein_suchen, position)
        if treffer < 0:
            teile.append(text[position:])
            return "".join(teile)
        teile.append(text[position:treffer])
        teile.append(ersatz)
        position = treffer + len(suchen)


class _AnonymFilter(logging.Filter):
    """Hängt am Handler, damit keine Meldung daran vorbeikommt."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = anonymisiere(record.getMessage())
        record.args = ()
        return True


# -- Einrichtung --------------------------------------------------------------

def richte_logging_ein(basis: Path | None = None, *,
                       max_bytes: int = MAX_BYTES,
                       anzahl_backups: int = ANZAHL_BACKUPS) -> Path | None:
    """Legt das rotierende Log an und liefert seinen Pfad.

    Mehrfache Aufrufe sind harmlos — beim zweiten Mal passiert nichts. Gibt
    ``None`` zurück, wenn sich die Datei nicht anlegen lässt; dann läuft die
    App ohne Protokoll weiter, statt am Start zu scheitern.
    """
    global _handler, _pfad
    if _handler is not None:
        return _pfad

    ziel = log_datei(basis)
    try:
        ziel.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            ziel, maxBytes=max_bytes, backupCount=anzahl_backups,
            encoding="utf-8")
    except OSError:
        return None

    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_ZEITFORMAT))
    handler.addFilter(_AnonymFilter())

    log = logging.getLogger(LOGGER_NAME)
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    # Nicht an den Root-Logger weiterreichen: sonst schriebe eine fremde
    # Konfiguration dieselbe Meldung ein zweites Mal — unanonymisiert.
    log.propagate = False

    _handler, _pfad = handler, ziel
    return ziel


def beende_logging() -> None:
    """Nur den eigenen Handler schliessen.

    Fremde Handler am selben Logger bleiben unangetastet.
    """
    global _handler, _pfad
    if _handler is None:
        return
    logging.getLogger(LOGGER_NAME).removeHandler(_handler)
    try:
        _handler.close()
    except OSError:
        pass
    _handler, _pfad = None, None


# -- Absturzprotokoll ---------------------------------------------------------

def protokolliere_absturz(typ: type[BaseException], wert: BaseException,
                          spur: object) -> str:
    """Schreibt den Traceback ins Log, liefert die Kurzfassung für die Anzeige.

    Die Kurzfassung ist bewusst einzeilig — sie steht später in einem Fenster,
    das ein Mitschüler lesen können muss.
    """
    text = "".join(traceback.format_exception(typ, wert, spur))
    logging.getLogger(LOGGER_NAME).critical("Unbehandelte Ausnahme\n%s", text)
    return anonymisiere(f"{typ.__name__}: {wert}").strip()


def notiere_start(version: str) -> None:
    """Eine Zeile pro Start — ohne die ist ein Log schwer einzuordnen."""
    logging.getLogger(LOGGER_NAME).info(
        "LernApp %s gestartet (%s, Python %s)",
        version, sys.platform, sys.version.split()[0])
