"""Tests für den Absturz-Hook.

Der Dialog selbst wird hier nicht geöffnet — er wird injiziert. Getestet wird,
was ohne laufende Oberfläche prüfbar ist: dass protokolliert wird, dass eine
verständliche Meldung entsteht und dass Strg+C kein Absturz ist.

Bezeichner bleiben bewusst ohne Umlaute; nur Text für Menschen bekommt sie.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from lernapp.gui import absturz
from lernapp.storage import protokoll


@pytest.fixture(autouse=True)
def _hook_ruecksetzen():
    original = sys.excepthook
    protokoll.beende_logging()
    absturz.setze_hauptfenster(None)
    yield
    sys.excepthook = original
    protokoll.beende_logging()
    absturz.setze_hauptfenster(None)


def _ausloesen(text: str = "kaputt") -> None:
    """Ruft den installierten Hook so auf, wie Python es täte."""
    try:
        raise ValueError(text)
    except ValueError as fehler:
        sys.excepthook(type(fehler), fehler, fehler.__traceback__)


def test_absturz_landet_im_log(tmp_path: Path):
    log = protokoll.richte_logging_ein(tmp_path)
    absturz.installiere_excepthook(log, melden=lambda _text: None)

    _ausloesen("Testabsturz")
    protokoll.beende_logging()

    assert "Testabsturz" in log.read_text(encoding="utf-8")


def test_meldung_nennt_die_logdatei(tmp_path: Path):
    log = protokoll.richte_logging_ein(tmp_path)
    gesehen: list[str] = []
    absturz.installiere_excepthook(log, melden=gesehen.append)

    _ausloesen()

    assert len(gesehen) == 1
    assert str(log) in gesehen[0]
    assert "ValueError: kaputt" in gesehen[0]


def test_meldung_kommt_auch_ohne_logdatei():
    """Ließ sich kein Log anlegen, muss der Nutzer trotzdem etwas sehen."""
    gesehen: list[str] = []
    absturz.installiere_excepthook(None, melden=gesehen.append)

    _ausloesen()

    assert len(gesehen) == 1
    assert "schiefgelaufen" in gesehen[0].lower()


def test_strg_c_ist_kein_absturz():
    gesehen: list[str] = []
    gereicht: list[type] = []
    sys.excepthook = lambda typ, wert, spur: gereicht.append(typ)
    absturz.installiere_excepthook(None, melden=gesehen.append)

    try:
        raise KeyboardInterrupt
    except KeyboardInterrupt as fehler:
        sys.excepthook(type(fehler), fehler, fehler.__traceback__)

    assert gesehen == []
    assert gereicht == [KeyboardInterrupt]


def test_hook_wirft_selbst_nichts(tmp_path: Path):
    """Ein fehlgeschlagener Fehlerdialog darf nie den Absturz verdoppeln."""
    log = protokoll.richte_logging_ein(tmp_path)

    def _kaputte_anzeige(_text: str) -> None:
        raise RuntimeError("Dialog kaputt")

    absturz.installiere_excepthook(log, melden=_kaputte_anzeige)

    _ausloesen()   # darf nicht durchschlagen
    protokoll.beende_logging()

    assert "kaputt" in log.read_text(encoding="utf-8")


def test_ohne_elternfenster_gibt_es_kein_qt_fenster():
    """Der wichtigste Fall: ``open()`` allein macht nichts sichtbar.

    Genau daran ist die erste Fassung gescheitert — sie meldete Erfolg,
    obwohl im gebauten Bundle nie ein Fenster erschien. Ohne Elternfenster
    muss ``zeige_meldung`` deshalb ehrlich False liefern, damit der
    plattformeigene Weg übernimmt.
    """
    absturz.setze_hauptfenster(None)

    assert absturz.zeige_meldung("egal") is False
