"""Windows-spezifische Dienste."""
from __future__ import annotations

import ctypes
import os
import threading
from ctypes import wintypes

from .base import BasisDienste


class _Blob(ctypes.Structure):
    """DATA_BLOB aus der Windows-API: Länge plus Zeiger auf die Bytes."""

    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob(daten: bytes) -> _Blob:
    puffer = ctypes.create_string_buffer(daten, len(daten))
    return _Blob(len(daten), ctypes.cast(puffer, ctypes.POINTER(ctypes.c_char)))


def _auslesen(blob: _Blob) -> bytes:
    roh = ctypes.string_at(blob.pbData, blob.cbData)
    ctypes.windll.kernel32.LocalFree(blob.pbData)
    return roh


def _dpapi_schuetzen(daten: bytes) -> bytes:
    ergebnis = _Blob()
    if not ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(_blob(daten)), None, None, None, None, 0,
            ctypes.byref(ergebnis)):
        raise OSError("CryptProtectData fehlgeschlagen")
    return _auslesen(ergebnis)


def _dpapi_entschluesseln(daten: bytes) -> bytes:
    ergebnis = _Blob()
    if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(_blob(daten)), None, None, None, None, 0,
            ctypes.byref(ergebnis)):
        raise OSError("CryptUnprotectData fehlgeschlagen")
    return _auslesen(ergebnis)

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
        und spätere Toast-Benachrichtigungen laufen ins Leere. Muss vor dem
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

    # -- Geheimnisse ----------------------------------------------------------
    #
    # DPAPI (CryptProtectData) verschlüsselt an das Windows-Benutzerkonto: die
    # Datei ist auf demselben Rechner unter einem anderen Konto und auf jedem
    # anderen Rechner wertlos. Bewusst ohne zusätzliche Abhängigkeit - `keyring`
    # zöge pywin32 mit und müsste im Bundle mitgeschleppt werden.

    def _geheimnis_pfad(self, name: str):
        sicher = "".join(z for z in name if z.isalnum() or z in "-_")
        return self.datenverzeichnis() / f"{sicher or 'geheim'}.dpapi"

    def speichere_geheimnis(self, name: str, wert: str) -> bool:
        try:
            roh = _dpapi_schuetzen(wert.encode("utf-8"))
        except Exception:
            return False
        pfad = self._geheimnis_pfad(name)
        try:
            pfad.parent.mkdir(parents=True, exist_ok=True)
            temp = pfad.with_suffix(".dpapi.tmp")
            temp.write_bytes(roh)
            os.replace(temp, pfad)
            return True
        except OSError:
            return False

    def lies_geheimnis(self, name: str) -> str | None:
        pfad = self._geheimnis_pfad(name)
        try:
            roh = pfad.read_bytes()
        except OSError:
            return None
        try:
            return _dpapi_entschluesseln(roh).decode("utf-8")
        except Exception:
            # Auf einem anderen Konto oder Rechner lässt sich die Datei nicht
            # entschlüsseln. Dann ist sie wertlos und wird weggeräumt, statt
            # bei jedem Start erneut zu scheitern.
            try:
                pfad.unlink()
            except OSError:
                pass
            return None

    def loesche_geheimnis(self, name: str) -> None:
        try:
            self._geheimnis_pfad(name).unlink()
        except OSError:
            pass
