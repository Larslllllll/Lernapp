"""Ablage von Geheimnissen in der Plattformschicht.

Ein GitHub-Token ist ein Passwort. Er darf nicht im Klartext neben den
Vokabeln liegen - unter Windows verschlüsselt DPAPI ihn an das Benutzerkonto.
"""
from __future__ import annotations

import sys

import pytest

from lernapp.platform_services.base import BasisDienste


@pytest.fixture
def windows_dienste(tmp_path):
    if sys.platform != "win32":
        pytest.skip("DPAPI gibt es nur unter Windows")
    from lernapp.platform_services.windows import WindowsDienste

    dienste = WindowsDienste()
    dienste.datenverzeichnis = lambda: tmp_path
    return dienste


def test_grundimplementierung_speichert_bewusst_nichts():
    """Wo es keine Verschlüsselung gibt, wird nichts abgelegt.

    Lieber jedes Mal neu anmelden als ein Passwort im Klartext.
    """
    dienste = BasisDienste()
    assert dienste.speichere_geheimnis("github", "gho_geheim") is False
    assert dienste.lies_geheimnis("github") is None
    dienste.loesche_geheimnis("github")  # darf nicht werfen


def test_geheimnis_ueberlebt_den_umweg_ueber_die_platte(windows_dienste):
    assert windows_dienste.speichere_geheimnis("github", "gho_geheim123") is True
    assert windows_dienste.lies_geheimnis("github") == "gho_geheim123"


def test_der_token_steht_nicht_im_klartext_in_der_datei(windows_dienste):
    """Der eigentliche Zweck der Übung."""
    windows_dienste.speichere_geheimnis("github", "gho_geheim123")
    roh = windows_dienste._geheimnis_pfad("github").read_bytes()
    assert b"gho_geheim123" not in roh
    assert len(roh) > len("gho_geheim123")


def test_loeschen_entfernt_es_wirklich(windows_dienste):
    windows_dienste.speichere_geheimnis("github", "gho_geheim123")
    windows_dienste.loesche_geheimnis("github")
    assert windows_dienste.lies_geheimnis("github") is None
    assert not windows_dienste._geheimnis_pfad("github").exists()


def test_loeschen_ohne_vorhandenes_geheimnis_ist_harmlos(windows_dienste):
    windows_dienste.loesche_geheimnis("gibtsnicht")


def test_fehlendes_geheimnis_ist_kein_fehler(windows_dienste):
    assert windows_dienste.lies_geheimnis("gibtsnicht") is None


def test_unlesbare_datei_wird_weggeraeumt(windows_dienste):
    """So sieht es aus, wenn die Datei von einem anderen Konto stammt.

    Sie ist dann wertlos. Einmal wegräumen ist besser, als bei jedem Start
    erneut daran zu scheitern.
    """
    pfad = windows_dienste._geheimnis_pfad("github")
    pfad.write_bytes(b"das ist kein DPAPI-Block")
    assert windows_dienste.lies_geheimnis("github") is None
    assert not pfad.exists()


def test_name_wird_zu_einem_sicheren_dateinamen(windows_dienste):
    """Der Name landet in einem Pfad - er darf nicht ausbrechen können."""
    pfad = windows_dienste._geheimnis_pfad("../../boese")
    assert pfad.parent == windows_dienste.datenverzeichnis()
    assert ".." not in pfad.name
