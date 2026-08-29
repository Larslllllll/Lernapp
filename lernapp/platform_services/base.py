"""Gemeinsame Schnittstelle der plattformspezifischen Dienste.

Regel: ausserhalb dieses Pakets darf kein Modul `winsound`, `AppKit` oder
aehnliches importieren. Fehler in einem Dienst duerfen das Lernen niemals
verhindern - alle Implementierungen schlucken ihre eigenen Ausnahmen.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol


class PlattformDienste(Protocol):
    name: str

    def spiele_ton(self, richtig: bool) -> None: ...

    def datenverzeichnis(self) -> Path: ...

    def unterstuetzt_ton(self) -> bool: ...


class BasisDienste:
    """Neutrale Grundimplementierung - tut nichts, schlaegt nie fehl."""

    name = "generisch"

    def spiele_ton(self, richtig: bool) -> None:
        return None

    def unterstuetzt_ton(self) -> bool:
        return False

    def datenverzeichnis(self) -> Path:
        from lernapp.storage import paths

        return paths.datenverzeichnis()
