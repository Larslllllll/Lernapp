"""LernApp - Einstiegspunkt (PySide6/QML).

    python LernApp.py     neue Qt-Oberfläche
    python run_ctk.py     alte CustomTkinter-Oberfläche (Vergleich)

Umgebungsvariablen für Entwicklung:
    LERNAPP_DATA_DIR   anderes Datenverzeichnis (schont die echten Daten)
    LERNAPP_FENSTER    "x,y" - Fensterposition
"""
import sys


def _start() -> int:
    """Startet die Oberfläche und fängt ab, was vor ihr schiefgehen kann.

    ``gui.app.run()`` richtet Logging und Excepthook selbst ein - der Hook
    greift also für alles, was während des Betriebs passiert. Was er nicht
    abdeckt, ist ein Fehler *beim Import* von PySide6: eine fehlende Qt-DLL
    im gebauten Bundle etwa. Genau dann sieht der Nutzer sonst gar nichts,
    weil das Bundle ohne Konsole läuft. Deshalb dieser äussere Ring.
    """
    from lernapp.storage import protokoll

    log_pfad = protokoll.richte_logging_ein()
    try:
        from lernapp.gui.app import run

        return run()
    except Exception as fehler:  # noqa: BLE001 - letzte Instanz vor dem Nichts
        kurz = protokoll.protokolliere_absturz(type(fehler), fehler,
                                               fehler.__traceback__)
        from lernapp.platform_services import dienste

        text = (f"LernApp konnte nicht starten.\n\nFehler: {kurz}")
        if log_pfad is not None:
            text += f"\n\nSchick Lars bitte diese Datei:\n{log_pfad}"
        if not dienste().zeige_meldung("LernApp – Start fehlgeschlagen", text):
            print(text, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_start())
