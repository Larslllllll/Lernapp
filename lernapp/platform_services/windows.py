"""Windows-spezifische Dienste."""
from __future__ import annotations

import threading

from .base import BasisDienste

try:
    import winsound

    _TON = True
except ImportError:  # pragma: no cover - nur auf Nicht-Windows
    _TON = False


class WindowsDienste(BasisDienste):
    name = "windows"

    def unterstuetzt_ton(self) -> bool:
        return _TON

    def spiele_ton(self, richtig: bool) -> None:
        if not _TON:
            return

        def _spielen() -> None:
            try:
                if richtig:
                    winsound.Beep(880, 80)
                    winsound.Beep(1100, 100)
                else:
                    winsound.Beep(200, 350)
            except Exception:
                pass

        threading.Thread(target=_spielen, daemon=True).start()
