"""Auswahl der plattformspezifischen Dienste.

Nutzung:

    from lernapp.platform_services import dienste
    dienste().spiele_ton(True)
"""
from __future__ import annotations

import sys

from .base import BasisDienste, PlattformDienste

_instanz: PlattformDienste | None = None


def dienste() -> PlattformDienste:
    global _instanz
    if _instanz is None:
        if sys.platform == "win32":
            from .windows import WindowsDienste

            _instanz = WindowsDienste()
        elif sys.platform == "darwin":
            from .macos import MacDienste

            _instanz = MacDienste()
        else:
            _instanz = BasisDienste()
    return _instanz


__all__ = ["dienste", "BasisDienste", "PlattformDienste"]
