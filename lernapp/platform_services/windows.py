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

    def beim_start(self) -> None:
        """Anwendungs-ID setzen.

        Ohne sie gruppiert Windows die App unter "Python" statt unter LernApp,
        und spaetere Toast-Benachrichtigungen laufen ins Leere. Muss vor dem
        ersten Fenster passieren.
        """
        from lernapp import APP_USER_MODEL_ID

        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                APP_USER_MODEL_ID)
        except Exception:
            pass

    def zeige_meldung(self, titel: str, text: str) -> bool:
        """MessageBoxW — funktioniert auch dann noch, wenn Qt nicht lädt."""
        try:
            import ctypes

            # MB_OK | MB_ICONERROR | MB_SETFOREGROUND
            ctypes.windll.user32.MessageBoxW(0, text, titel, 0x10 | 0x10000)
            return True
        except Exception:
            return False

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
