"""Tests für Logging und Absturzprotokoll.

Zwei Eigenschaften sind hier wichtiger als die reine Funktion:

  * Das Log darf nie im echten Datenverzeichnis landen (deshalb überall
    ein `basis`-Argument bzw. LERNAPP_DATA_DIR).
  * Es darf nichts Persönliches enthalten - insbesondere keine Pfade
    außerhalb des Datenverzeichnisses. Ein Traceback nennt aber immer den
    Installationsort, und der enthält den Windows-Benutzernamen.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from lernapp.storage import protokoll


@pytest.fixture(autouse=True)
def _sauberes_logging():
    """Jeder Test startet ohne Handler und räumt hinter sich auf."""
    protokoll.beende_logging()
    yield
    protokoll.beende_logging()


# -- Einrichtung --------------------------------------------------------------

def test_log_landet_im_datenverzeichnis(tmp_path: Path):
    pfad = protokoll.richte_logging_ein(tmp_path)

    assert pfad == tmp_path / "logs" / "lernapp.log"
    assert pfad.exists()


def test_geschriebene_meldung_steht_in_der_datei(tmp_path: Path):
    pfad = protokoll.richte_logging_ein(tmp_path)

    logging.getLogger("lernapp.test").warning("Testmeldung 42")
    protokoll.beende_logging()

    assert "Testmeldung 42" in pfad.read_text(encoding="utf-8")


def test_zweiter_aufruf_haengt_keinen_zweiten_handler_an(tmp_path: Path):
    protokoll.richte_logging_ein(tmp_path)
    protokoll.richte_logging_ein(tmp_path)

    # Nur die eigenen zählen - pytest hängt eigene Handler an denselben
    # Logger, sobald er nicht mehr an root weiterreicht.
    eigene = [h for h in logging.getLogger(protokoll.LOGGER_NAME).handlers
              if isinstance(h, RotatingFileHandler)]
    assert len(eigene) == 1


def test_nicht_schreibbares_verzeichnis_bricht_nicht_ab(tmp_path: Path):
    """Ein kaputtes Log darf das Lernen nie verhindern."""
    blockiert = tmp_path / "datei-statt-ordner"
    blockiert.write_text("belegt", encoding="utf-8")

    pfad = protokoll.richte_logging_ein(blockiert)

    assert pfad is None
    logging.getLogger("lernapp.test").warning("darf nicht werfen")


# -- Rotation -----------------------------------------------------------------

def test_log_waechst_nicht_unbegrenzt(tmp_path: Path):
    pfad = protokoll.richte_logging_ein(tmp_path, max_bytes=2_000, anzahl_backups=2)
    log = logging.getLogger("lernapp.test")

    for i in range(500):
        log.info("Zeile %d mit etwas Füllung zum Erreichen der Grenze", i)
    protokoll.beende_logging()

    dateien = sorted(pfad.parent.glob("lernapp.log*"))
    assert len(dateien) <= 3                      # aktuell + 2 Backups
    assert all(d.stat().st_size < 10_000 for d in dateien)


# -- Anonymisierung -----------------------------------------------------------

def test_anonymisiere_ersetzt_das_benutzerverzeichnis():
    heim = str(Path.home())
    text = "Fehler in " + heim + r"\Programme\LernApp\app.py"

    assert protokoll.anonymisiere(text) == r"Fehler in ~\Programme\LernApp\app.py"


def test_anonymisiere_erkennt_beide_trennzeichen():
    heim = str(Path.home()).replace("\\", "/")

    assert protokoll.anonymisiere(heim + "/x") == "~/x"


def test_anonymisiere_ist_gleichgueltig_gegen_gross_klein():
    heim = str(Path.home()).upper()

    assert protokoll.anonymisiere(heim + r"\x") == r"~\x"


def test_benutzername_steht_nicht_im_log(tmp_path: Path):
    pfad = protokoll.richte_logging_ein(tmp_path)

    logging.getLogger("lernapp.test").error("Pfad: %s", Path.home() / "geheim.txt")
    protokoll.beende_logging()

    inhalt = pfad.read_text(encoding="utf-8")
    assert str(Path.home()) not in inhalt
    assert "~" in inhalt


# -- Absturzprotokoll ---------------------------------------------------------

def _ausnahme(fehlerklasse=ValueError, text="kaputt"):
    try:
        raise fehlerklasse(text)
    except fehlerklasse as f:
        return type(f), f, f.__traceback__


def test_absturz_wird_ins_log_geschrieben(tmp_path: Path):
    pfad = protokoll.richte_logging_ein(tmp_path)

    protokoll.protokolliere_absturz(*_ausnahme(text="Testabsturz"))
    protokoll.beende_logging()

    inhalt = pfad.read_text(encoding="utf-8")
    assert "Testabsturz" in inhalt
    assert "Traceback" in inhalt


def test_absturz_liefert_kurzfassung_fuer_die_anzeige(tmp_path: Path):
    protokoll.richte_logging_ein(tmp_path)

    kurz = protokoll.protokolliere_absturz(*_ausnahme(text="Testabsturz"))

    assert kurz == "ValueError: Testabsturz"


def test_absturztext_enthaelt_kein_benutzerverzeichnis(tmp_path: Path):
    pfad = protokoll.richte_logging_ein(tmp_path)

    protokoll.protokolliere_absturz(*_ausnahme())
    protokoll.beende_logging()

    assert str(Path.home()) not in pfad.read_text(encoding="utf-8")


def test_ohne_eingerichtetes_logging_wirft_der_absturz_nichts():
    assert protokoll.protokolliere_absturz(*_ausnahme()) == "ValueError: kaputt"
