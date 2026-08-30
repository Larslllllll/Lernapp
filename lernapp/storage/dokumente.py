"""Text aus einer Datei holen - PDF, Textdatei, CSV.

Die Trennung ist Absicht: **hier** wird nur gelesen und entpackt, ohne zu
verstehen. Was davon eine Vokabel ist, entscheidet lernapp.netz.lernset_ki -
und zwar erst danach, an einem sauberen Text.

PDFs ohne Textebene (abfotografierte oder eingescannte Seiten) enthalten nur
Bildpunkte. Dann kommt hier nichts heraus, und das wird auch so gemeldet,
statt eine leere Vokabelliste zu erzeugen und den Nutzer ratlos zu lassen.
"""
from __future__ import annotations

from pathlib import Path

# Mehr als das liest niemand mehr sinnvoll durch, und das Modell soll nicht
# mit einem ganzen Buch gefüttert werden.
MAX_ZEICHEN = 40_000
MAX_SEITEN = 30

ENDUNGEN = {".pdf", ".txt", ".csv", ".tsv", ".md"}


class DokumentFehler(Exception):
    """Fehler, dessen Text direkt dem Nutzer gezeigt werden kann."""


def lies_text(pfad: Path) -> str:
    """Reinen Text aus der Datei holen. Wirft DokumentFehler mit Klartext."""
    if not pfad.exists():
        raise DokumentFehler(f"Die Datei {pfad.name} gibt es nicht.")
    endung = pfad.suffix.lower()
    if endung not in ENDUNGEN:
        raise DokumentFehler(
            f"{endung or 'Diese Datei'} kann ich nicht lesen. "
            f"Möglich sind: {', '.join(sorted(ENDUNGEN))}."
        )

    text = _aus_pdf(pfad) if endung == ".pdf" else _aus_textdatei(pfad)
    text = text.strip()
    if not text:
        raise DokumentFehler(
            f"In {pfad.name} steckt kein lesbarer Text. Bei abfotografierten "
            "oder eingescannten Seiten ist das normal - dort sind nur "
            "Bildpunkte gespeichert."
        )
    if len(text) > MAX_ZEICHEN:
        text = text[:MAX_ZEICHEN]
    return text


def _aus_pdf(pfad: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as grund:  # pragma: no cover - fehlt nur bei kaputtem Build
        raise DokumentFehler(
            "Diese Programmversion kann keine PDFs lesen."
        ) from grund

    try:
        leser = PdfReader(str(pfad))
    except Exception as grund:
        raise DokumentFehler(f"{pfad.name} lässt sich nicht öffnen.") from grund

    if getattr(leser, "is_encrypted", False):
        # Manche PDFs sind mit leerem Passwort verschlüsselt - das geht.
        try:
            leser.decrypt("")
        except Exception as grund:
            raise DokumentFehler(
                f"{pfad.name} ist passwortgeschützt."
            ) from grund

    teile = []
    for seite in leser.pages[:MAX_SEITEN]:
        try:
            teile.append(seite.extract_text() or "")
        except Exception:
            # Eine kaputte Seite darf die anderen nicht mitnehmen.
            continue
    return "\n".join(teile)


def _aus_textdatei(pfad: Path) -> str:
    for kodierung in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return pfad.read_text(encoding=kodierung)
        except UnicodeDecodeError:
            continue
        except OSError as grund:
            raise DokumentFehler(f"{pfad.name} ist nicht lesbar.") from grund
    raise DokumentFehler(f"{pfad.name} hat eine unbekannte Zeichenkodierung.")
