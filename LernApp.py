"""LernApp - Einstiegspunkt (PySide6/QML).

    python LernApp.py     neue Qt-Oberflaeche
    python run_ctk.py     alte CustomTkinter-Oberflaeche (Vergleich)

Umgebungsvariablen fuer Entwicklung:
    LERNAPP_DATA_DIR   anderes Datenverzeichnis (schont die echten Daten)
    LERNAPP_FENSTER    "x,y" - Fensterposition
"""
from lernapp.gui.app import run

if __name__ == "__main__":
    raise SystemExit(run())
