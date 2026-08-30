"""Absturzbehandlung für die Qt-Oberfläche.

Im gebauten Bundle gibt es keine Konsole. Ohne diesen Hook verschwindet ein
Traceback spurlos, und ein Klassenkamerad kann nur berichten, dass „nichts
passiert ist". Hier wird deshalb beides getan:

  1. Der vollständige Traceback geht ins Log (anonymisiert, siehe
     ``storage.protokoll``).
  2. Der Nutzer bekommt ein Fenster, das den Pfad zur Logdatei nennt.

Verschickt wird nichts. Wer den Fehler melden will, schickt die Datei selbst.

Die App wird nach einem Absturz **nicht** beendet: eine Ausnahme in einem
einzelnen Slot macht das Programm meist nicht unbrauchbar, und ungespeicherte
Antworten sollen nicht verloren gehen.

Warum zwei Wege zur Anzeige
---------------------------
Ein ``MessageDialog`` aus QtQuick.Dialogs **ohne Elternfenster wird nie
sichtbar** — ``open()`` meldet keinen Fehler, ``visible`` bleibt trotzdem
false. Gegen ein gebautes Bundle nachgemessen. Deshalb gilt:

* Während des Betriebs gibt es ein Hauptfenster; dann kommt das Qt-Fenster.
* Beim Start (Main.qml lädt nicht, Qt-DLL fehlt) gibt es keins — dann
  übernimmt die plattformeigene Meldung aus ``platform_services``.

Der Rückgabewert von ``zeige_meldung`` ist deshalb der tatsächlich abgefragte
Sichtbarkeitszustand, nicht „der Aufruf hat nicht geworfen".
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from lernapp.storage import protokoll

TITEL = "LernApp – etwas ist schiefgelaufen"

# Referenz auf offene Dialoge samt Engine. Ohne die räumt Python beides sofort
# wieder ab und das Fenster verschwindet im selben Moment.
_offene_dialoge: list = []

# Das Hauptfenster, sobald es existiert. Nur darüber wird der Dialog sichtbar.
_hauptfenster: object | None = None

_MELDUNG_QML = b"""
import QtQuick
import QtQuick.Dialogs

MessageDialog {
    buttons: MessageDialog.Ok
}
"""


def setze_hauptfenster(fenster: object | None) -> None:
    """Merkt das geladene Hauptfenster als Elternfenster für Fehlerdialoge."""
    global _hauptfenster
    _hauptfenster = fenster


def _text(kurzfassung: str, log_pfad: Path | None) -> str:
    """Die Meldung für den Nutzer — ohne Fachjargon, mit klarer Bitte."""
    zeilen = [
        "Etwas ist schiefgelaufen.",
        "",
        f"Fehler: {kurzfassung}",
    ]
    if log_pfad is not None:
        zeilen += [
            "",
            "Schick Lars bitte diese Datei, dann lässt sich der Fehler finden:",
            str(log_pfad),
        ]
    zeilen += [
        "",
        "Du kannst weiterlernen. Falls sich die App komisch verhält,"
        " starte sie neu.",
    ]
    return "\n".join(zeilen)


def zeige_meldung(text: str, eltern: object | None = None) -> bool:
    """Qt-Fenster mit der Meldung. Liefert, ob es wirklich sichtbar wurde.

    Kein QtWidgets: die Oberfläche läuft auf QGuiApplication, und
    Qt6Widgets.dll ist bewusst nicht im Bundle. QtQuick.Dialogs ist es —
    dieselben Module, die der Import/Export-Dateidialog ohnehin braucht.
    """
    fenster = eltern if eltern is not None else _hauptfenster
    if fenster is None:
        return False
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlComponent, QQmlEngine

        if QGuiApplication.instance() is None:
            return False

        engine = QQmlEngine()
        komponente = QQmlComponent(engine)
        komponente.setData(_MELDUNG_QML, QUrl())
        dialog = komponente.create()
        if dialog is None:
            return False

        dialog.setProperty("title", TITEL)
        dialog.setProperty("text", text)
        dialog.setProperty("parentWindow", fenster)
        # Engine und Dialog müssen beide am Leben bleiben.
        _offene_dialoge.append((engine, dialog))
        dialog.open()
        return bool(dialog.property("visible"))
    except Exception:
        # Ein fehlgeschlagener Fehlerdialog darf nie selbst zum Absturz werden.
        return False


def _melde(text: str) -> None:
    """Qt-Fenster, sonst der plattformeigene Weg, sonst stderr."""
    if zeige_meldung(text):
        return
    from lernapp.platform_services import dienste

    if dienste().zeige_meldung(TITEL, text):
        return
    print(text, file=sys.stderr)


def installiere_excepthook(log_pfad: Path | None = None,
                           melden: Callable[[str], None] | None = None) -> None:
    """Hängt den Hook ein. ``melden`` ist nur für Tests gedacht.

    Strg+C bleibt unangetastet — ein Abbruch ist kein Absturz.
    """
    vorheriger = sys.excepthook
    anzeigen = melden or _melde

    def _hook(typ, wert, spur) -> None:
        if issubclass(typ, KeyboardInterrupt):
            vorheriger(typ, wert, spur)
            return
        kurz = protokoll.protokolliere_absturz(typ, wert, spur)
        try:
            anzeigen(_text(kurz, log_pfad))
        except Exception:
            # Scheitert die Anzeige, bleibt es beim Logeintrag. Ein zweiter
            # Fehler aus dem Fehlerpfad heraus hilft niemandem.
            pass

    sys.excepthook = _hook
