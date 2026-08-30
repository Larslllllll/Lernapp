"""Aus Rohtext ein Lernset - ohne Netz.

Das Modell wird hereingereicht. Geprüft wird vor allem, was mit einer
schlampigen Antwort passiert: Modelle halten sich nicht an Formatregeln, und
was hier durchrutscht, steht nachher als Karte im Lernset.
"""
from __future__ import annotations

import pytest

from lernapp.netz import lernset_ki as lk
from lernapp.netz.ki import KIFehler, Zugang

ZUGANG = Zugang("https://beispiel.invalid/v1", "testmodell", "geheim", "test")


def _mit_antwort(text: str, monkeypatch):
    monkeypatch.setattr(lk, "frage", lambda *a, **k: text)


def test_saubere_antwort_wird_uebernommen(monkeypatch):
    _mit_antwort("la maison;das Haus\nle chien;der Hund", monkeypatch)
    vorschlag = lk.erkenne_vokabeln(ZUGANG, "irgendein Text")
    assert vorschlag.zeilen == ["la maison;das Haus", "le chien;der Hund"]
    assert vorschlag.text == "la maison;das Haus\nle chien;der Hund"


def test_drei_formen_bleiben_erhalten(monkeypatch):
    """Verbpakete sind der Grund, warum drei Felder erlaubt sind."""
    _mit_antwort("go;went;gone\nbe;was/were;been", monkeypatch)
    assert lk.erkenne_vokabeln(ZUGANG, "x").zeilen == ["go;went;gone", "be;was/were;been"]


def test_einleitungssatz_wird_verworfen(monkeypatch):
    """Modelle plaudern trotz klarer Ansage."""
    _mit_antwort("Hier sind die Vokabeln:\nla maison;das Haus", monkeypatch)
    vorschlag = lk.erkenne_vokabeln(ZUGANG, "x")
    assert vorschlag.zeilen == ["la maison;das Haus"]
    assert vorschlag.verworfen == ["Hier sind die Vokabeln:"]


def test_codeblock_und_nummerierung_werden_entfernt(monkeypatch):
    _mit_antwort("```\n1. la maison;das Haus\n2) le chien;der Hund\n```", monkeypatch)
    assert lk.erkenne_vokabeln(ZUGANG, "x").zeilen == [
        "la maison;das Haus", "le chien;der Hund"]


def test_ueberschriften_werden_verworfen(monkeypatch):
    _mit_antwort("Unit 4\nSeite 23\nWortschatz\nla maison;das Haus", monkeypatch)
    vorschlag = lk.erkenne_vokabeln(ZUGANG, "x")
    assert vorschlag.zeilen == ["la maison;das Haus"]
    assert len(vorschlag.verworfen) == 3


def test_ganze_saetze_sind_keine_vokabeln(monkeypatch):
    lang = "x" * 90
    _mit_antwort(f"{lang};das Haus\nla maison;das Haus", monkeypatch)
    assert lk.erkenne_vokabeln(ZUGANG, "x").zeilen == ["la maison;das Haus"]


def test_zeilen_ohne_trennzeichen_werden_verworfen(monkeypatch):
    _mit_antwort("la maison\nla maison;das Haus", monkeypatch)
    vorschlag = lk.erkenne_vokabeln(ZUGANG, "x")
    assert vorschlag.zeilen == ["la maison;das Haus"]
    assert "la maison" in vorschlag.verworfen


def test_zu_viele_felder_werden_verworfen(monkeypatch):
    _mit_antwort("a;b;c;d\nla maison;das Haus", monkeypatch)
    assert lk.erkenne_vokabeln(ZUGANG, "x").zeilen == ["la maison;das Haus"]


def test_deckel_gegen_erfundene_listen(monkeypatch):
    """Jenseits einer Buchseite fängt ein Modell an zu erfinden."""
    _mit_antwort("\n".join(f"wort{i};Wort {i}" for i in range(300)), monkeypatch)
    assert len(lk.erkenne_vokabeln(ZUGANG, "x").zeilen) == lk.MAX_ZEILEN


def test_leere_antwort_meldet_sich_verstaendlich(monkeypatch):
    _mit_antwort("Ich konnte nichts finden.", monkeypatch)
    with pytest.raises(KIFehler, match="keine Vokabelpaare"):
        lk.erkenne_vokabeln(ZUGANG, "x")


def test_leerer_text_wird_gar_nicht_erst_gesendet(monkeypatch):
    def darf_nicht(*a, **k):
        raise AssertionError("es wurde trotzdem gefragt")

    monkeypatch.setattr(lk, "frage", darf_nicht)
    with pytest.raises(KIFehler, match="leer"):
        lk.erkenne_vokabeln(ZUGANG, "   ")


def test_zusammenfassung_ist_ein_satz_fuer_menschen(monkeypatch):
    _mit_antwort("Hier sind sie:\nla maison;das Haus", monkeypatch)
    vorschlag = lk.erkenne_vokabeln(ZUGANG, "x")
    assert vorschlag.zusammenfassung() == "1 Vokabeln erkannt, 1 Zeilen verworfen"


def test_das_ergebnis_versteht_der_vorhandene_textimport(monkeypatch):
    """Der eigentliche Trick: die Ausgabe geht durch dieselbe Vorschau wie
    ein von Hand eingefügter Text."""
    from lernapp.core.import_export import parse_text

    _mit_antwort("la maison;das Haus\ngo;went;gone", monkeypatch)
    vorschlag = lk.erkenne_vokabeln(ZUGANG, "x")
    ergebnis = parse_text(vorschlag.text)
    assert ergebnis.normale == 1
    assert ergebnis.pakete == 1
    assert not ergebnis.probleme
