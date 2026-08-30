"""Text aus Dateien holen.

Das PDF für den Test wird von Hand gebaut - ein PDF ist ein Textformat, und
eine Bibliothek zum Erzeugen müsste sonst nur für Tests ins Projekt.
"""
from __future__ import annotations

import pytest

from lernapp.storage import dokumente


def _mini_pdf(zeilen: list[str]) -> bytes:
    """Ein gültiges PDF mit einer Seite Text.

    Bewusst minimal: Katalog, Seitenbaum, eine Seite, ein Textstrom, eine
    Standardschrift. Mehr braucht ein Leser nicht.
    """
    befehle = ["BT", "/F1 12 Tf", "50 800 Td"]
    for zeile in zeilen:
        sicher = zeile.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        befehle.append(f"({sicher}) Tj")
        befehle.append("0 -16 Td")
    befehle.append("ET")
    strom = "\n".join(befehle).encode("latin-1", "replace")

    objekte = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length " + str(len(strom)).encode() + b">>\nstream\n" + strom + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]

    aus = bytearray(b"%PDF-1.4\n")
    versaetze = []
    for nummer, inhalt in enumerate(objekte, start=1):
        versaetze.append(len(aus))
        aus += f"{nummer} 0 obj\n".encode() + inhalt + b"\nendobj\n"

    start_xref = len(aus)
    aus += f"xref\n0 {len(objekte) + 1}\n".encode()
    aus += b"0000000000 65535 f \n"
    for versatz in versaetze:
        aus += f"{versatz:010d} 00000 n \n".encode()
    aus += (f"trailer\n<</Size {len(objekte) + 1}/Root 1 0 R>>\n"
            f"startxref\n{start_xref}\n%%EOF\n").encode()
    return bytes(aus)


# -- PDF ----------------------------------------------------------------------

def test_text_aus_einem_pdf(tmp_path):
    pfad = tmp_path / "unit4.pdf"
    pfad.write_bytes(_mini_pdf(["Unit 4 Vocabulary",
                                "the neighbour   der Nachbar",
                                "to borrow   ausleihen"]))
    text = dokumente.lies_text(pfad)
    assert "neighbour" in text
    assert "Nachbar" in text
    assert "borrow" in text


def test_pdf_ohne_textebene_meldet_sich_verstaendlich(tmp_path):
    """Der häufigste Fall bei abfotografierten Seiten - und der, bei dem der
    Nutzer sonst ratlos vor einem leeren Lernset steht."""
    pfad = tmp_path / "scan.pdf"
    pfad.write_bytes(_mini_pdf([]))
    with pytest.raises(dokumente.DokumentFehler, match="kein lesbarer Text"):
        dokumente.lies_text(pfad)


def test_kaputtes_pdf_wirft_keinen_traceback(tmp_path):
    pfad = tmp_path / "kaputt.pdf"
    pfad.write_bytes(b"das ist kein PDF")
    with pytest.raises(dokumente.DokumentFehler):
        dokumente.lies_text(pfad)


def test_lange_pdfs_werden_gedeckelt(tmp_path):
    pfad = tmp_path / "buch.pdf"
    pfad.write_bytes(_mini_pdf([f"Zeile {i} mit etwas Text" for i in range(3000)]))
    text = dokumente.lies_text(pfad)
    assert len(text) <= dokumente.MAX_ZEICHEN


# -- Textdateien --------------------------------------------------------------

def test_text_aus_einer_textdatei(tmp_path):
    pfad = tmp_path / "vokabeln.txt"
    pfad.write_text("la maison;das Haus\nle chien;der Hund", encoding="utf-8")
    assert "la maison" in dokumente.lies_text(pfad)


def test_umlaute_aus_einer_alten_windows_datei(tmp_path):
    """Was aus Word oder Excel kommt, ist oft cp1252 statt UTF-8."""
    pfad = tmp_path / "alt.csv"
    pfad.write_bytes("überfüllt;crowded".encode("cp1252"))
    assert "überfüllt" in dokumente.lies_text(pfad)


def test_leere_datei_meldet_sich(tmp_path):
    pfad = tmp_path / "leer.txt"
    pfad.write_text("   \n\n", encoding="utf-8")
    with pytest.raises(dokumente.DokumentFehler, match="kein lesbarer Text"):
        dokumente.lies_text(pfad)


def test_unbekannte_endung_wird_abgelehnt(tmp_path):
    pfad = tmp_path / "bild.png"
    pfad.write_bytes(b"\x89PNG")
    with pytest.raises(dokumente.DokumentFehler, match="kann ich nicht lesen"):
        dokumente.lies_text(pfad)


def test_fehlende_datei_meldet_sich(tmp_path):
    with pytest.raises(dokumente.DokumentFehler, match="gibt es nicht"):
        dokumente.lies_text(tmp_path / "weg.pdf")
